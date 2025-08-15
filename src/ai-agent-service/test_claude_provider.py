#!/usr/bin/env python3
"""
Claude Code Provider 测试脚本
"""
import asyncio
import os
import sys

# 添加路径以便导入我们的模块
sys.path.append('./src/ai-agent-service/app')

from coding_service.providers.claude_provider import ClaudeCodeProvider

async def test_code_generation():
    """测试代码生成功能"""
    print("=== Claude Code Provider 测试 ===")
    
    try:
        # 初始化 provider
        provider = ClaudeCodeProvider()
        print("✅ Provider 初始化成功")
        
        # 测试简单的代码生成
        prompt = "创建一个简单的Hello World页面，包含一个按钮，点击后显示当前时间"
        session_id = "test_session_001"
        
        print(f"📝 测试提示: {prompt}")
        print("🔄 开始生成代码...")
        
        async for event in provider.generate(prompt, session_id):
            event_type = event.get("type")
            content = event.get("content", "")
            
            if event_type == "thought":
                print(f"💭 思考: {content[:100]}...")
            elif event_type == "code_chunk":
                print(f"🔧 代码片段: {len(content)} 字符")
            elif event_type == "complete":
                final_code = event.get("final_code", "")
                print(f"✅ 生成完成! 代码长度: {len(final_code)} 字符")
                print(f"📊 元数据: {event.get('metadata', {})}")
                
                # 保存生成的代码到文件以便检查
                with open("/tmp/generated_code.html", "w", encoding="utf-8") as f:
                    f.write(final_code)
                print("💾 代码已保存到 /tmp/generated_code.html")
                break
            elif event_type == "error":
                print(f"❌ 错误: {content}")
                break
    
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_code_generation())
