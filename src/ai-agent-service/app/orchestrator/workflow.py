import asyncio
import logging
import httpx
import os
from typing import Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)

class PostcardWorkflow:
    """明信片生成工作流编排器"""
    
    def __init__(self):
        self.postcard_service_url = os.getenv("POSTCARD_SERVICE_URL", "http://postcard-service:8000")
        self.logger = logging.getLogger(self.__class__.__name__)
        # 用于跨服务认证的内部服务令牌
        self.internal_service_token = os.getenv("INTERNAL_SERVICE_TOKEN", "")
        
        # 将在子类中初始化工作流步骤
        self.steps = []
    
    async def execute(self, task_data: Dict[str, Any]):
        """执行完整的明信片生成工作流"""
        task_id = task_data.get("task_id")
        context = {"task": task_data, "results": {}}
        
        try:
            # 更新任务状态为处理中（屏蔽取消影响）
            await asyncio.shield(self.update_task_status(task_id, "processing"))
            
            # 导入步骤类（避免循环导入）
            from .steps.concept_generator import ConceptGenerator
            from .steps.content_generator import ContentGenerator
            from .steps.image_generator import ImageGenerator
            from .steps.structured_content_generator import StructuredContentGenerator
            
            # 初始化工作流步骤（移除Claude Code SDK，使用结构化内容生成）
            self.steps = [
                ConceptGenerator(),           # 第1步：概念生成
                ContentGenerator(),           # 第2步：文案生成  
                ImageGenerator(),             # 第3步：图片生成
                StructuredContentGenerator()  # 第4步：结构化内容生成（替代前端编码）
            ]
            
            # 依次执行各个步骤
            for i, step in enumerate(self.steps, 1):
                step_name = step.__class__.__name__
                self.logger.info(f"📍 执行步骤 {i}/4: {step_name}")
                
                try:
                    context = await step.execute(context)
                    
                    # 保存中间结果
                    await self.save_intermediate_result(task_id, step_name, context["results"])
                    
                    self.logger.info(f"✅ 步骤 {i}/4 完成: {step_name}")
                except Exception as e:
                    self.logger.error(f"❌ 步骤 {i}/4 失败: {step_name} - {e}")
                    raise
            
            # 保存最终结果（屏蔽取消影响）
            await asyncio.shield(self.save_final_result(task_id, context["results"]))
            await asyncio.shield(self.update_task_status(task_id, "completed"))
            
            self.logger.info(f"🎉 工作流执行完成: {task_id}")
            
        except Exception as e:
            self.logger.error(f"❌ 工作流执行失败: {task_id} - {e}")
            try:
                await asyncio.shield(self.update_task_status(task_id, "failed", str(e)))
            except Exception:
                pass
            raise
    
    async def update_task_status(self, task_id: str, status: str, error_message: str = None):
        """更新任务状态"""
        try:
            url = f"{self.postcard_service_url}/api/v1/postcards/status/{task_id}"
            data = {"status": status}
            if error_message:
                data["error_message"] = error_message

            # 增加重试，提升可靠性，延长超时时间适应大模型响应
            headers = {}
            if self.internal_service_token:
                headers["X-Internal-Service-Token"] = self.internal_service_token
            async with httpx.AsyncClient(timeout=30.0, headers=headers) as client:
                for attempt in range(3):
                    try:
                        response = await client.post(url, json=data)
                        if response.status_code == 200:
                            self.logger.info(f"✅ 任务状态更新成功: {task_id} -> {status}")
                            return True
                        else:
                            body = None
                            try:
                                body = response.text
                            except Exception:
                                pass
                            self.logger.error(f"❌ 任务状态更新失败: {task_id} - {response.status_code} - {body}")
                    except Exception as req_err:
                        self.logger.error(f"⚠️ 状态更新请求异常(第{attempt+1}次): {task_id} - {req_err}")
                    await asyncio.sleep(1)
            return False

        except Exception as e:
            self.logger.error(f"❌ 更新任务状态异常: {task_id} - {e}")
            return False
    
    async def save_intermediate_result(self, task_id: str, step_name: str, results: Dict[str, Any]):
        """保存中间结果"""
        try:
            # 调用明信片服务保存中间结果
            # 这里可以根据需要实现具体的保存逻辑
            self.logger.info(f"💾 保存中间结果: {task_id} - {step_name}")
            
        except Exception as e:
            self.logger.error(f"❌ 保存中间结果失败: {task_id} - {step_name} - {e}")
    
    async def save_final_result(self, task_id: str, results: Dict[str, Any]):
        """保存最终结果"""
        try:
            # 通过状态更新接口一并提交最终结果
            self.logger.info(f"💾 保存最终结果: {task_id}")
            self.logger.info(f"📊 结果摘要: {list(results.keys())}")

            payload: Dict[str, Any] = {"status": "completed"}
            # 允许的字段（包含结构化数据）
            for key in ["concept", "content", "image_url", "frontend_code", "preview_url", "card_image_url", "card_html", "structured_data"]:
                if key in results and results[key] is not None:
                    payload[key] = results[key]

            url = f"{self.postcard_service_url}/api/v1/postcards/status/{task_id}"
            headers = {}
            if self.internal_service_token:
                headers["X-Internal-Service-Token"] = self.internal_service_token
            async with httpx.AsyncClient(timeout=30.0, headers=headers) as client:
                resp = await client.post(url, json=payload)
                if resp.status_code == 200:
                    self.logger.info("✅ 最终结果提交成功")
                else:
                    self.logger.error(f"❌ 最终结果提交失败: {resp.status_code} - {resp.text}")

        except Exception as e:
            self.logger.error(f"❌ 保存最终结果失败: {task_id} - {e}")
