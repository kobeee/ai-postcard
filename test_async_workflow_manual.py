#!/usr/bin/env python3
"""
AI明信片异步工作流手动测试脚本

该脚本构造测试数据，验证完整的异步工作流：
1. 用户创建明信片任务 -> postcard-service
2. 消息队列异步处理 -> ai-agent-service  
3. 四步AI工作流：概念生成 -> 文案生成 -> 图片生成 -> 前端代码生成
4. 最终返回完整的动态明信片

测试用例包括多种场景的明信片生成需求。
"""

import asyncio
import httpx
import json
import time
from datetime import datetime
from typing import Dict, Any, List

# 服务配置
POSTCARD_SERVICE_URL = "http://localhost:8082"
AI_AGENT_SERVICE_URL = "http://localhost:8080"

class AsyncWorkflowTester:
    """异步工作流完整测试器"""
    
    def __init__(self):
        self.session_id = f"test_{int(time.time())}"
        print(f"🚀 启动AI明信片异步工作流测试")
        print(f"🆔 测试会话ID: {self.session_id}")
        print(f"⏰ 测试时间: {datetime.now()}")
        print("="*80)
    
    def get_test_cases(self) -> List[Dict[str, Any]]:
        """获取多样化的测试用例"""
        return [
            {
                "name": "生日祝福明信片",
                "user_input": "为我最好的朋友创建一张生日祝福明信片，她今年25岁，喜欢粉色和可爱的东西，希望能表达我对她的感谢和祝福",
                "style": "温馨可爱",
                "theme": "生日祝福",
                "expected_features": ["生日元素", "粉色配色", "可爱风格", "感谢祝福"]
            },
            {
                "name": "旅行分享明信片", 
                "user_input": "给远方的朋友发一张旅行明信片，分享我在美丽海边看日出的心情，希望传达宁静和美好",
                "style": "清新自然",
                "theme": "旅行分享", 
                "expected_features": ["海边元素", "日出场景", "自然风光", "宁静氛围"]
            },
            {
                "name": "毕业祝福明信片",
                "user_input": "为即将毕业的同学制作一张纪念明信片，祝愿前程似锦，友谊长存，充满希望和励志",
                "style": "青春励志", 
                "theme": "毕业祝福",
                "expected_features": ["毕业元素", "励志内容", "青春色彩", "友谊主题"]
            },
            {
                "name": "母亲节感恩明信片",
                "user_input": "为我的妈妈创建一张母亲节感恩明信片，表达对她无私奉献的感谢，希望传达温暖的母爱",
                "style": "温馨典雅",
                "theme": "感恩母爱",
                "expected_features": ["母爱元素", "感恩内容", "温暖色调", "典雅设计"]
            },
            {
                "name": "节日祝福明信片",
                "user_input": "制作一张中秋节明信片，希望能表达团圆和思念之情，适合发给在外地的家人",
                "style": "中国风",
                "theme": "节日祝福", 
                "expected_features": ["中秋元素", "团圆主题", "中国风格", "思念情感"]
            }
        ]
    
    async def test_complete_workflow(self, test_case: Dict[str, Any]) -> Dict[str, Any]:
        """测试完整的异步工作流"""
        
        print(f"\n📋 测试案例: {test_case['name']}")
        print(f"📝 用户需求: {test_case['user_input']}")
        print(f"🎨 风格: {test_case['style']}")
        print(f"🎯 主题: {test_case['theme']}")
        print(f"✨ 预期特征: {', '.join(test_case['expected_features'])}")
        print("-" * 60)
        
        try:
            # 1. 创建明信片任务
            task_id = await self._create_task(test_case)
            
            # 2. 等待任务完成并监控进度
            result = await self._monitor_task_progress(task_id)
            
            # 3. 验证结果质量
            await self._validate_result(result, test_case)
            
            # 4. 保存测试结果
            await self._save_test_result(test_case['name'], task_id, result)
            
            return {
                "success": True,
                "task_id": task_id,
                "test_case": test_case['name'],
                "result": result
            }
            
        except Exception as e:
            print(f"❌ 测试失败: {e}")
            return {
                "success": False,
                "test_case": test_case['name'],
                "error": str(e)
            }
    
    async def _create_task(self, test_case: Dict[str, Any]) -> str:
        """创建明信片生成任务"""
        print("📤 步骤1: 创建明信片任务")
        
        request_data = {
            "user_input": test_case["user_input"],
            "style": test_case["style"], 
            "theme": test_case["theme"],
            "user_id": f"test_user_{self.session_id}"
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{POSTCARD_SERVICE_URL}/api/v1/postcards/create",
                json=request_data
            )
            
            if response.status_code != 200:
                raise Exception(f"创建任务失败: {response.status_code} - {response.text}")
            
            result = response.json()
            task_id = result["task_id"]
            
            print(f"✅ 任务创建成功: {task_id}")
            return task_id
    
    async def _monitor_task_progress(self, task_id: str) -> Dict[str, Any]:
        """监控任务进度直到完成"""
        print("⏳ 步骤2: 监控任务处理进度")
        
        max_wait_time = 300  # 5分钟超时
        check_interval = 5   # 5秒检查一次
        start_time = time.time()
        
        last_status = None
        progress_indicators = {
            "concept": "📝 概念生成",
            "content": "✍️ 文案生成", 
            "image_url": "🎨 图片生成",
            "frontend_code": "💻 代码生成"
        }
        
        while time.time() - start_time < max_wait_time:
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.get(
                        f"{POSTCARD_SERVICE_URL}/api/v1/postcards/status/{task_id}"
                    )
                    
                    if response.status_code != 200:
                        await asyncio.sleep(check_interval)
                        continue
                    
                    status_data = response.json()
                    current_status = status_data["status"]
                    
                    # 显示状态变化
                    if current_status != last_status:
                        elapsed = time.time() - start_time
                        print(f"📊 [{elapsed:6.1f}s] 状态: {current_status}")
                        last_status = current_status
                    
                    # 显示工作流进度
                    progress_shown = set()
                    for key, desc in progress_indicators.items():
                        if status_data.get(key) and key not in progress_shown:
                            print(f"    ✅ {desc} 完成")
                            progress_shown.add(key)
                    
                    # 检查完成状态
                    if current_status == "completed":
                        elapsed = time.time() - start_time
                        print(f"🎉 任务完成! 总耗时: {elapsed:.1f}秒")
                        return status_data
                    elif current_status == "failed":
                        error_msg = status_data.get("error_message", "未知错误")
                        raise Exception(f"任务处理失败: {error_msg}")
                    
                    await asyncio.sleep(check_interval)
                    
            except Exception as e:
                if "任务处理失败" in str(e):
                    raise
                print(f"⚠️ 状态查询异常: {e}")
                await asyncio.sleep(check_interval)
        
        raise Exception(f"任务处理超时 (>{max_wait_time}秒)")
    
    async def _validate_result(self, result: Dict[str, Any], test_case: Dict[str, Any]):
        """验证生成结果的质量"""
        print("🔍 步骤3: 验证生成结果质量")
        
        # 检查必需字段
        required_fields = ["concept", "content", "image_url", "frontend_code"]
        for field in required_fields:
            if not result.get(field):
                raise Exception(f"缺少必需字段: {field}")
            print(f"✅ {field}: 已生成 ({len(str(result[field]))} 字符)")
        
        # 验证前端代码质量
        frontend_code = result["frontend_code"]
        html_checks = [
            ("<!DOCTYPE html>", "HTML文档类型"),
            ("<html", "HTML根元素"),
            ("<head>", "文档头部"),
            ("<body>", "文档主体"),
            ("</html>", "HTML结束标签")
        ]
        
        for check, desc in html_checks:
            if check in frontend_code:
                print(f"    ✅ {desc}")
            else:
                print(f"    ⚠️ 可能缺少{desc}")
        
        # 检查样式和脚本
        if "<style>" in frontend_code or "style=" in frontend_code:
            print(f"    ✅ 包含CSS样式")
        if "<script>" in frontend_code or "script=" in frontend_code:
            print(f"    ✅ 包含JavaScript交互")
        
        print("✅ 结果验证通过")
    
    async def _save_test_result(self, test_name: str, task_id: str, result: Dict[str, Any]):
        """保存测试结果到文件"""
        print("💾 步骤4: 保存测试结果")
        
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # 保存完整结果
            result_filename = f"test_result_{test_name}_{task_id}_{timestamp}.json"
            with open(result_filename, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2, default=str)
            
            print(f"✅ 完整结果保存: {result_filename}")
            
            # 保存HTML文件用于预览
            if result.get("frontend_code"):
                html_filename = f"postcard_{test_name}_{task_id}_{timestamp}.html"
                with open(html_filename, 'w', encoding='utf-8') as f:
                    f.write(result["frontend_code"])
                
                print(f"✅ 明信片预览: {html_filename}")
                print(f"🌐 可在浏览器中打开查看效果")
            
        except Exception as e:
            print(f"⚠️ 保存结果失败: {e}")

async def run_all_tests():
    """运行所有测试用例"""
    
    tester = AsyncWorkflowTester()
    test_cases = tester.get_test_cases()
    
    print(f"🎯 准备运行 {len(test_cases)} 个测试案例")
    
    results = []
    successful = 0
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{'🎪' * 15} 测试 {i}/{len(test_cases)} {'🎪' * 15}")
        
        try:
            result = await tester.test_complete_workflow(test_case)
            results.append(result)
            
            if result["success"]:
                successful += 1
                print(f"✅ 案例 {i} 测试成功: {test_case['name']}")
            else:
                print(f"❌ 案例 {i} 测试失败: {test_case['name']}")
            
        except Exception as e:
            print(f"❌ 案例 {i} 执行异常: {e}")
            results.append({
                "success": False,
                "test_case": test_case['name'],
                "error": str(e)
            })
    
    # 测试总结
    print(f"\n{'🎊' * 20} 测试总结 {'🎊' * 20}")
    print(f"📊 总测试案例: {len(test_cases)}")
    print(f"✅ 成功案例: {successful}")
    print(f"❌ 失败案例: {len(test_cases) - successful}")
    print(f"📈 成功率: {successful/len(test_cases)*100:.1f}%")
    
    if successful > 0:
        print(f"\n🎉 恭喜！AI明信片异步工作流测试成功！")
        print(f"💡 可以查看生成的HTML文件预览明信片效果")
        print(f"📁 测试结果文件包含完整的生成数据")
    else:
        print(f"\n😞 所有测试案例都失败了")
        print(f"🔧 请检查服务配置和启动状态")
    
    return results

# 单个案例快速测试
async def quick_test():
    """快速测试单个案例"""
    tester = AsyncWorkflowTester()
    
    test_case = {
        "name": "快速测试",
        "user_input": "创建一张简单的祝福明信片，表达美好祝愿",
        "style": "简约现代",
        "theme": "美好祝愿",
        "expected_features": ["简约设计", "祝福内容"]
    }
    
    print("🚀 开始快速测试...")
    result = await tester.test_complete_workflow(test_case)
    
    if result["success"]:
        print("🎉 快速测试成功！")
    else:
        print("😞 快速测试失败！")
    
    return result

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "quick":
        # 快速测试模式
        asyncio.run(quick_test())
    else:
        # 完整测试模式
        asyncio.run(run_all_tests())