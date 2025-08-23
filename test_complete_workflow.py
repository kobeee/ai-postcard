#!/usr/bin/env python3
"""
完整的AI明信片异步工作流测试脚本

该脚本将测试从用户创建明信片请求到最终生成前端代码的整个流程：
1. 创建明信片任务（通过postcard-service）
2. AI Agent异步处理（概念→文案→图片→前端代码）
3. 查询任务状态直到完成
4. 验证生成结果的质量

使用方法：
python test_complete_workflow.py
"""

import asyncio
import httpx
import json
import uuid
import time
from datetime import datetime
from typing import Dict, Any

# 服务配置
POSTCARD_SERVICE_URL = "http://localhost:8082"
AI_AGENT_SERVICE_URL = "http://localhost:8080"

class WorkflowTester:
    """工作流测试器"""
    
    def __init__(self):
        self.session_id = f"test_session_{uuid.uuid4().hex[:8]}"
        print(f"🆔 测试会话ID: {self.session_id}")
    
    async def test_complete_workflow(self, test_case: Dict[str, Any]) -> Dict[str, Any]:
        """测试完整工作流"""
        
        print(f"\n{'='*80}")
        print(f"🚀 开始测试明信片生成工作流")
        print(f"📝 用户需求: {test_case['user_input']}")
        print(f"🎨 风格: {test_case.get('style', '不限')}")
        print(f"🎯 主题: {test_case.get('theme', '不限')}")
        print(f"{'='*80}")
        
        # 1. 创建明信片任务
        task_id = await self._create_postcard_task(test_case)
        
        # 2. 等待任务完成
        final_result = await self._wait_for_completion(task_id)
        
        # 3. 验证结果质量
        await self._validate_results(final_result)
        
        # 4. 保存结果（可选）
        await self._save_results(task_id, final_result)
        
        print(f"\n🎉 工作流测试完成!")
        return final_result
    
    async def _create_postcard_task(self, test_case: Dict[str, Any]) -> str:
        """创建明信片任务"""
        print(f"\n📋 步骤1: 创建明信片任务")
        
        # 添加测试用户ID
        test_case["user_id"] = f"test_user_{self.session_id}"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{POSTCARD_SERVICE_URL}/api/v1/postcards/create",
                    json=test_case
                )
                
                if response.status_code != 200:
                    raise Exception(f"创建任务失败: {response.status_code} - {response.text}")
                
                result = response.json()
                task_id = result["task_id"]
                
                print(f"✅ 任务创建成功")
                print(f"   🆔 任务ID: {task_id}")
                print(f"   📊 初始状态: {result['status']}")
                print(f"   💬 消息: {result['message']}")
                
                return task_id
                
        except Exception as e:
            print(f"❌ 创建任务失败: {e}")
            raise
    
    async def _wait_for_completion(self, task_id: str) -> Dict[str, Any]:
        """等待任务完成"""
        print(f"\n⏳ 步骤2: 等待任务处理完成")
        
        max_wait_time = 300  # 5分钟超时
        check_interval = 3   # 3秒检查一次
        start_time = time.time()
        
        attempt = 0
        while time.time() - start_time < max_wait_time:
            attempt += 1
            elapsed = time.time() - start_time
            
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.get(
                        f"{POSTCARD_SERVICE_URL}/api/v1/postcards/status/{task_id}"
                    )
                    
                    if response.status_code != 200:
                        print(f"⚠️ 状态查询失败: {response.status_code}")
                        await asyncio.sleep(check_interval)
                        continue
                    
                    status_data = response.json()
                    current_status = status_data["status"]
                    
                    print(f"📊 [{attempt:3d}] {elapsed:6.1f}s - 状态: {current_status}")
                    
                    if current_status == "completed":
                        print(f"✅ 任务处理完成! 总耗时: {elapsed:.1f}秒")
                        return status_data
                    elif current_status == "failed":
                        error_msg = status_data.get("error_message", "未知错误")
                        print(f"❌ 任务处理失败: {error_msg}")
                        raise Exception(f"任务处理失败: {error_msg}")
                    elif current_status in ["pending", "processing"]:
                        # 显示中间进度
                        if status_data.get("concept"):
                            print(f"    📝 概念已生成")
                        if status_data.get("content"):
                            print(f"    ✍️ 文案已生成")
                        if status_data.get("image_url"):
                            print(f"    🎨 图片已生成")
                        if status_data.get("frontend_code"):
                            print(f"    💻 代码已生成")
                    else:
                        print(f"⚠️ 未知状态: {current_status}")
                    
                    await asyncio.sleep(check_interval)
                    
            except Exception as e:
                print(f"⚠️ 查询状态异常: {e}")
                await asyncio.sleep(check_interval)
        
        raise Exception(f"任务处理超时 (>{max_wait_time}秒)")
    
    async def _validate_results(self, result_data: Dict[str, Any]):
        """验证结果质量"""
        print(f"\n🔍 步骤3: 验证生成结果质量")
        
        required_fields = ["concept", "content", "image_url", "frontend_code"]
        
        for field in required_fields:
            value = result_data.get(field)
            if not value:
                raise Exception(f"缺少必需字段: {field}")
            
            print(f"✅ {field}: {'✓' if value else '✗'}")
            
            # 详细验证
            if field == "concept":
                print(f"   📏 长度: {len(value)} 字符")
                if "主题概念" in value or "概念" in value:
                    print(f"   📝 包含概念描述")
            
            elif field == "content":
                print(f"   📏 长度: {len(value)} 字符")
                if "主标题" in value or "标题" in value:
                    print(f"   📝 包含标题内容")
            
            elif field == "image_url":
                print(f"   🔗 URL: {value[:60]}...")
                if value.startswith("http"):
                    print(f"   🌐 有效的URL格式")
            
            elif field == "frontend_code":
                print(f"   📏 长度: {len(value)} 字符")
                
                # 检查HTML结构
                html_checks = [
                    ("<!DOCTYPE html>", "DOCTYPE声明"),
                    ("<html", "HTML标签"),
                    ("<head>", "HEAD部分"),
                    ("<body>", "BODY部分"),
                    ("</html>", "HTML结束标签")
                ]
                
                for check, name in html_checks:
                    if check in value:
                        print(f"   ✅ {name}")
                    else:
                        print(f"   ❌ 缺少{name}")
                
                # 检查样式和脚本
                if "<style>" in value or "style=" in value:
                    print(f"   ✅ 包含CSS样式")
                else:
                    print(f"   ⚠️ 可能缺少CSS样式")
                
                if "<script>" in value or "script=" in value:
                    print(f"   ✅ 包含JavaScript")
                else:
                    print(f"   ⚠️ 可能缺少JavaScript")
        
        print(f"✅ 结果验证完成")
    
    async def _save_results(self, task_id: str, result_data: Dict[str, Any]):
        """保存测试结果"""
        print(f"\n💾 步骤4: 保存测试结果")
        
        try:
            # 保存到文件
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"test_result_{task_id}_{timestamp}.json"
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(result_data, f, ensure_ascii=False, indent=2)
            
            print(f"✅ 结果已保存到: {filename}")
            
            # 如果有前端代码，也保存HTML文件
            if result_data.get("frontend_code"):
                html_filename = f"test_postcard_{task_id}_{timestamp}.html"
                with open(html_filename, 'w', encoding='utf-8') as f:
                    f.write(result_data["frontend_code"])
                
                print(f"✅ 前端代码已保存到: {html_filename}")
                print(f"   🌐 可以在浏览器中打开查看效果")
            
        except Exception as e:
            print(f"⚠️ 保存结果失败: {e}")

async def run_test_cases():
    """运行多个测试案例"""
    
    test_cases = [
        {
            "user_input": "为我最好的朋友创建一张生日祝福明信片，希望能表达我对她的感谢和祝福，她喜欢粉色和可爱的东西",
            "style": "温馨可爱",
            "theme": "生日祝福"
        },
        {
            "user_input": "给远方的朋友发一张旅行明信片，分享我在美丽海边看日出的心情，希望传达宁静和美好",
            "style": "清新自然", 
            "theme": "旅行分享"
        },
        {
            "user_input": "为即将毕业的同学制作一张纪念明信片，祝愿前程似锦，友谊长存",
            "style": "青春励志",
            "theme": "毕业祝福"
        }
    ]
    
    print(f"🎯 开始批量测试 ({len(test_cases)} 个案例)")
    
    results = []
    successful = 0
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{'🎪'*20} 测试案例 {i}/{len(test_cases)} {'🎪'*20}")
        
        tester = WorkflowTester()
        
        try:
            result = await tester.test_complete_workflow(test_case)
            results.append({
                "case_id": i,
                "success": True,
                "result": result
            })
            successful += 1
            print(f"✅ 案例 {i} 测试成功")
            
        except Exception as e:
            print(f"❌ 案例 {i} 测试失败: {e}")
            results.append({
                "case_id": i,
                "success": False,
                "error": str(e)
            })
    
    # 打印总结
    print(f"\n{'🎊'*30} 测试总结 {'🎊'*30}")
    print(f"📊 总测试案例: {len(test_cases)}")
    print(f"✅ 成功案例: {successful}")
    print(f"❌ 失败案例: {len(test_cases) - successful}")
    print(f"📈 成功率: {successful/len(test_cases)*100:.1f}%")
    
    if successful > 0:
        print(f"\n🎉 恭喜！AI明信片异步工作流测试成功！")
        print(f"💡 你可以查看生成的HTML文件来查看明信片效果")
    else:
        print(f"\n😞 所有测试案例都失败了，请检查服务配置")
    
    return results

async def main():
    """主函数"""
    print(f"🚀 AI明信片异步工作流完整测试")
    print(f"⏰ 开始时间: {datetime.now()}")
    print(f"🔧 Postcard Service: {POSTCARD_SERVICE_URL}")
    print(f"🤖 AI Agent Service: {AI_AGENT_SERVICE_URL}")
    
    try:
        results = await run_test_cases()
        return results
    except KeyboardInterrupt:
        print(f"\n🛑 测试被用户中断")
    except Exception as e:
        print(f"\n❌ 测试运行失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # 运行测试
    asyncio.run(main())