"""
异步工作流完整测试
测试从创建任务到完成整个明信片生成流程
"""

import pytest
import asyncio
import httpx
import uuid
from datetime import datetime

# 测试配置
POSTCARD_SERVICE_URL = "http://localhost:8082"
AI_AGENT_SERVICE_URL = "http://localhost:8080"

class TestAsyncWorkflow:
    """异步工作流测试"""
    
    @pytest.fixture
    def test_postcard_request(self):
        """测试用的明信片请求数据"""
        return {
            "user_input": "为我最好的朋友创建一张生日祝福明信片，希望能表达我对她的感谢和祝福",
            "style": "温馨可爱",
            "theme": "生日祝福",
            "user_id": f"test_user_{uuid.uuid4().hex[:8]}"
        }
    
    async def test_complete_workflow(self, test_postcard_request):
        """测试完整的异步工作流"""
        
        # 1. 创建明信片任务
        print("\n🚀 步骤1: 创建明信片任务")
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{POSTCARD_SERVICE_URL}/api/v1/postcards/create",
                json=test_postcard_request,
                timeout=10.0
            )
            
            assert response.status_code == 200
            task_data = response.json()
            task_id = task_data["task_id"]
            
            print(f"✅ 任务创建成功: {task_id}")
            print(f"📋 任务状态: {task_data['status']}")
        
        # 2. 等待任务处理完成
        print("\n⏳ 步骤2: 等待任务处理")
        max_wait_time = 300  # 5分钟超时
        wait_interval = 5    # 5秒检查一次
        
        for attempt in range(max_wait_time // wait_interval):
            await asyncio.sleep(wait_interval)
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{POSTCARD_SERVICE_URL}/api/v1/postcards/status/{task_id}",
                    timeout=10.0
                )
                
                assert response.status_code == 200
                status_data = response.json()
                current_status = status_data["status"]
                
                print(f"📊 检查进度 [{attempt + 1}/{max_wait_time // wait_interval}]: {current_status}")
                
                if current_status == "completed":
                    print("✅ 任务处理完成!")
                    break
                elif current_status == "failed":
                    print("❌ 任务处理失败!")
                    print(f"错误信息: {status_data.get('error_message', '未知错误')}")
                    pytest.fail(f"任务处理失败: {status_data.get('error_message')}")
                elif current_status in ["pending", "processing"]:
                    continue
                else:
                    pytest.fail(f"未知任务状态: {current_status}")
        else:
            pytest.fail(f"任务处理超时，最后状态: {current_status}")
        
        # 3. 验证最终结果
        print("\n🔍 步骤3: 验证最终结果")
        final_status = status_data
        
        # 验证必需字段存在
        assert final_status["task_id"] == task_id
        assert final_status["status"] == "completed"
        assert final_status["concept"] is not None
        assert final_status["content"] is not None
        assert final_status["image_url"] is not None
        assert final_status["frontend_code"] is not None
        
        print(f"✅ 概念生成: {len(final_status['concept'])} 字符")
        print(f"✅ 文案生成: {len(final_status['content'])} 字符")
        print(f"✅ 图片URL: {final_status['image_url'][:50]}...")
        print(f"✅ 前端代码: {len(final_status['frontend_code'])} 字符")
        
        # 4. 验证前端代码质量
        print("\n🔍 步骤4: 验证前端代码质量")
        frontend_code = final_status["frontend_code"]
        
        # 检查HTML结构
        assert "<!DOCTYPE html>" in frontend_code
        assert "<html" in frontend_code
        assert "<head>" in frontend_code
        assert "<body>" in frontend_code
        assert "</html>" in frontend_code
        
        # 检查CSS样式
        assert "<style>" in frontend_code or "style=" in frontend_code
        
        # 检查JavaScript
        assert "<script>" in frontend_code or "script=" in frontend_code
        
        print("✅ 前端代码结构验证通过")
        
        # 5. 打印测试摘要
        print("\n📊 测试完成摘要:")
        print(f"🆔 任务ID: {task_id}")
        print(f"📝 用户输入: {test_postcard_request['user_input']}")
        print(f"🎨 风格: {test_postcard_request['style']}")
        print(f"🎯 主题: {test_postcard_request['theme']}")
        print(f"⏱️ 创建时间: {final_status['created_at']}")
        print(f"✅ 完成时间: {final_status['completed_at']}")
        print(f"🔄 重试次数: {final_status['retry_count']}")
        
        return {
            "task_id": task_id,
            "status": final_status,
            "frontend_code": frontend_code
        }

@pytest.mark.asyncio
async def test_workflow_integration():
    """测试工作流集成"""
    
    test_cases = [
        {
            "user_input": "为我的妈妈创建一张母亲节感谢明信片",
            "style": "温馨典雅",
            "theme": "感恩母爱"
        },
        {
            "user_input": "给远方的朋友发一张旅行明信片，分享我在美丽海边的心情",
            "style": "清新自然",
            "theme": "旅行分享"
        },
        {
            "user_input": "为即将毕业的同学制作一张纪念明信片，祝愿前程似锦",
            "style": "青春励志",
            "theme": "毕业祝福"
        }
    ]
    
    print(f"\n🎯 开始批量测试 {len(test_cases)} 个案例")
    
    results = []
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{'='*60}")
        print(f"📋 测试案例 {i}/{len(test_cases)}")
        print(f"📝 需求: {test_case['user_input']}")
        
        test_case["user_id"] = f"batch_test_user_{i}"
        
        workflow_test = TestAsyncWorkflow()
        try:
            result = await workflow_test.test_complete_workflow(test_case)
            results.append(result)
            print(f"✅ 案例 {i} 测试成功")
        except Exception as e:
            print(f"❌ 案例 {i} 测试失败: {e}")
            results.append({"error": str(e)})
    
    # 统计结果
    successful = len([r for r in results if "error" not in r])
    failed = len(results) - successful
    
    print(f"\n{'='*60}")
    print(f"📊 批量测试完成统计:")
    print(f"✅ 成功: {successful}/{len(test_cases)}")
    print(f"❌ 失败: {failed}/{len(test_cases)}")
    print(f"📊 成功率: {successful/len(test_cases)*100:.1f}%")
    
    # 断言至少有一个成功
    assert successful > 0, f"所有测试案例都失败了"

if __name__ == "__main__":
    # 单独运行测试
    async def run_single_test():
        test_request = {
            "user_input": "为我最好的朋友创建一张生日祝福明信片，希望能表达我对她的感谢和祝福",
            "style": "温馨可爱",
            "theme": "生日祝福",
            "user_id": "test_user_single"
        }
        
        workflow_test = TestAsyncWorkflow()
        result = await workflow_test.test_complete_workflow(test_request)
        
        print("\n🎉 单独测试完成!")
        print(f"前端代码示例:\n{result['frontend_code'][:500]}...")
    
    asyncio.run(run_single_test())