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
        
        # 将在子类中初始化工作流步骤
        self.steps = []
    
    async def execute(self, task_data: Dict[str, Any]):
        """执行完整的明信片生成工作流"""
        task_id = task_data.get("task_id")
        context = {"task": task_data, "results": {}}
        
        try:
            # 更新任务状态为处理中
            await self.update_task_status(task_id, "processing")
            
            # 导入步骤类（避免循环导入）
            from .steps.concept_generator import ConceptGenerator
            from .steps.content_generator import ContentGenerator
            from .steps.image_generator import ImageGenerator
            from .steps.frontend_coder import FrontendCoder
            
            # 初始化工作流步骤
            self.steps = [
                ConceptGenerator(),    # 第1步：概念生成
                ContentGenerator(),    # 第2步：文案生成  
                ImageGenerator(),      # 第3步：图片生成
                FrontendCoder()        # 第4步：前端编码（复用现有能力）
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
            
            # 保存最终结果
            await self.save_final_result(task_id, context["results"])
            await self.update_task_status(task_id, "completed")
            
            self.logger.info(f"🎉 工作流执行完成: {task_id}")
            
        except Exception as e:
            self.logger.error(f"❌ 工作流执行失败: {task_id} - {e}")
            await self.update_task_status(task_id, "failed", str(e))
            raise
    
    async def update_task_status(self, task_id: str, status: str, error_message: str = None):
        """更新任务状态"""
        try:
            async with httpx.AsyncClient() as client:
                url = f"{self.postcard_service_url}/api/v1/postcards/status/{task_id}"
                
                data = {"status": status}
                if error_message:
                    data["error_message"] = error_message
                
                response = await client.post(url, json=data)
                
                if response.status_code == 200:
                    self.logger.info(f"✅ 任务状态更新成功: {task_id} -> {status}")
                else:
                    self.logger.error(f"❌ 任务状态更新失败: {task_id} - {response.status_code}")
                    
        except Exception as e:
            self.logger.error(f"❌ 更新任务状态异常: {task_id} - {e}")
    
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
            # 调用明信片服务保存最终结果
            self.logger.info(f"💾 保存最终结果: {task_id}")
            self.logger.info(f"📊 结果摘要: {list(results.keys())}")
            
        except Exception as e:
            self.logger.error(f"❌ 保存最终结果失败: {task_id} - {e}")