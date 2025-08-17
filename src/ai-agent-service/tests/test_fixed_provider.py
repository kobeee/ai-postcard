#!/usr/bin/env python3
"""
测试修复后的Claude Provider错误处理
验证API端点验证功能是否正常工作
"""

import asyncio
import sys
import os

# 添加路径以便导入模块
sys.path.insert(0, '/app')

from coding_service.providers.claude_provider import ClaudeCodeProvider

async def test_provider_with_invalid_url():
    """测试使用无效URL时的错误处理"""
    print("==== 测试修复后的Claude Provider ====")
    
    provider = ClaudeCodeProvider()
    
    print("🧪 开始生成代码测试（应该检测到HTML响应错误）...")
    
    try:
        # 模拟代码生成请求
        async for event in provider.generate(
            prompt="创建一个简单的HTML页面", 
            session_id="test-session-001"
        ):
            print(f"📨 事件: {event['type']}")
            
            if event['type'] == 'error':
                print(f"✅ 成功检测到错误: {event['content']}")
                return True
            elif event['type'] == 'status':
                print(f"📋 状态: {event['content']}")
            elif event['type'] == 'complete':
                print("❌ 意外完成了代码生成，应该在验证阶段就失败")
                return False
                
    except Exception as e:
        print(f"❌ 发生未处理异常: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    
    print("❌ 没有检测到预期的API配置错误")
    return False

async def main():
    """主测试函数"""
    print("🔧 环境变量状态:")
    print(f"ANTHROPIC_API_KEY: {'已设置' if os.getenv('ANTHROPIC_API_KEY') else '未设置'}")
    print(f"ANTHROPIC_AUTH_TOKEN: {'已设置' if os.getenv('ANTHROPIC_AUTH_TOKEN') else '未设置'}")
    print(f"ANTHROPIC_BASE_URL: {os.getenv('ANTHROPIC_BASE_URL', '未设置')}")
    
    success = await test_provider_with_invalid_url()
    
    if success:
        print("\n✅ 测试通过: Claude Provider 正确检测并报告了API配置错误")
        return 0
    else:
        print("\n❌ 测试失败: Claude Provider 未能正确处理API配置错误")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
