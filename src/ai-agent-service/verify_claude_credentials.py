#!/usr/bin/env python3
"""
Claude API 密钥和环境配置验证脚本

此脚本用于验证 Claude Code SDK 所需的环境变量是否正确配置，
以及 API 密钥和 Base URL 的有效性。

运行方式：
1. 在项目根目录中运行: python src/ai-agent-service/verify_claude_credentials.py
2. 或在 ai-agent-service 目录中运行: python verify_claude_credentials.py
"""

import os
import sys
import asyncio
import logging
from dotenv import load_dotenv

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_environment_variables():
    """检查环境变量配置"""
    print("=" * 60)
    print("🔍 检查环境变量配置")
    print("=" * 60)
    
    # 加载环境变量
    env_file = ".env"
    if os.path.exists(env_file):
        load_dotenv(env_file)
        print(f"✅ 找到 {env_file} 文件")
    else:
        print(f"⚠️  未找到 {env_file} 文件，将检查系统环境变量")
    
    # 必需的环境变量
    required_vars = {
        "ANTHROPIC_API_KEY": "Claude API 密钥",
        "ANTHROPIC_BASE_URL": "Claude API 基础 URL (可选)"
    }
    
    # 其他相关变量
    optional_vars = {
        "AI_PROVIDER_TYPE": "AI Provider 类型",
        "CLAUDE_DEFAULT_MODEL": "默认模型",
        "CLAUDE_FALLBACK_MODEL": "备用模型"
    }
    
    print("\n📋 必需变量检查:")
    missing_required = []
    
    for var, desc in required_vars.items():
        value = os.getenv(var)
        if var == "ANTHROPIC_API_KEY":
            if value:
                # 显示脱敏的密钥
                masked_value = f"{value[:10]}...{value[-4:]}" if len(value) > 14 else value[:6] + "***"
                print(f"  ✅ {var}: {masked_value} ({desc})")
            else:
                print(f"  ❌ {var}: 未设置 ({desc})")
                missing_required.append(var)
        elif var == "ANTHROPIC_BASE_URL":
            if value:
                print(f"  ✅ {var}: {value} ({desc})")
            else:
                print(f"  ℹ️  {var}: 未设置，将使用默认端点 ({desc})")
    
    print("\n📋 可选变量检查:")
    for var, desc in optional_vars.items():
        value = os.getenv(var)
        if value:
            print(f"  ✅ {var}: {value} ({desc})")
        else:
            print(f"  ⚠️  {var}: 未设置，将使用默认值 ({desc})")
    
    if missing_required:
        print(f"\n❌ 缺少必需的环境变量: {', '.join(missing_required)}")
        return False
    else:
        print(f"\n✅ 所有必需的环境变量都已设置")
        return True

async def test_claude_sdk_basic():
    """测试 Claude Code SDK 基本连接"""
    print("\n" + "=" * 60)
    print("🧪 测试 Claude Code SDK 基本功能")
    print("=" * 60)
    
    try:
        # 尝试导入 Claude Code SDK
        print("📦 导入 Claude Code SDK...")
        from claude_code_sdk import ClaudeSDKClient, ClaudeCodeOptions
        print("✅ Claude Code SDK 导入成功")
        
        # 测试基本配置
        options = ClaudeCodeOptions(
            system_prompt="你是一个测试助手。",
            max_turns=1,
            allowed_tools=["Read"]
        )
        print("✅ ClaudeCodeOptions 配置成功")
        
        # 尝试创建客户端（但不发送请求）
        print("🔗 测试客户端初始化...")
        async with ClaudeSDKClient(options=options) as client:
            print("✅ ClaudeSDKClient 初始化成功")
            
            # 发送一个简单的测试查询
            print("💬 发送测试查询...")
            test_prompt = "请回复'测试成功'四个字。"
            await client.query(test_prompt)
            
            # 接收响应
            print("📨 接收响应...")
            response_received = False
            async for message in client.receive_response():
                if hasattr(message, 'content'):
                    for block in message.content:
                        if hasattr(block, 'text') and block.text.strip():
                            print(f"🎯 收到响应: {block.text.strip()[:100]}...")
                            response_received = True
                            break
                
                if type(message).__name__ == "ResultMessage":
                    if hasattr(message, 'total_cost_usd'):
                        print(f"💰 请求成本: ${message.total_cost_usd:.4f}")
                    if hasattr(message, 'duration_ms'):
                        print(f"⏱️  处理时间: {message.duration_ms}ms")
                    break
            
            if response_received:
                print("✅ Claude Code SDK 测试成功！API 密钥和连接正常")
                return True
            else:
                print("⚠️  没有收到预期的响应内容")
                return False
                
    except ImportError as e:
        print(f"❌ Claude Code SDK 导入失败: {e}")
        print("💡 请确保已安装 claude-code-sdk：pip install claude-code-sdk")
        return False
    except Exception as e:
        print(f"❌ Claude Code SDK 测试失败: {e}")
        print("💡 可能的原因：")
        print("   1. API 密钥无效或已过期")
        print("   2. 网络连接问题")
        print("   3. Base URL 配置错误（如果使用了自定义端点）")
        print("   4. 缺少 Node.js 依赖（需要安装 @anthropic-ai/claude-code）")
        return False

def check_nodejs_dependency():
    """检查 Node.js 依赖"""
    print("\n" + "=" * 60)
    print("🔍 检查 Node.js 依赖")
    print("=" * 60)
    
    import subprocess
    try:
        # 检查是否安装了 @anthropic-ai/claude-code
        result = subprocess.run(['npm', 'list', '-g', '@anthropic-ai/claude-code'], 
                              capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            print("✅ 全局 @anthropic-ai/claude-code 已安装")
            return True
        else:
            print("❌ 全局 @anthropic-ai/claude-code 未安装")
            print("💡 请运行: npm install -g @anthropic-ai/claude-code")
            return False
            
    except subprocess.TimeoutExpired:
        print("⚠️  检查 npm 包超时")
        return False
    except FileNotFoundError:
        print("❌ 未找到 npm 命令，请确保已安装 Node.js")
        return False
    except Exception as e:
        print(f"⚠️  检查 npm 包时出错: {e}")
        return False

async def main():
    """主函数"""
    print("🚀 Claude Code SDK 环境验证工具")
    print("此工具将验证 lovart.ai 项目所需的 Claude Code SDK 环境配置\n")
    
    # 1. 检查环境变量
    env_ok = check_environment_variables()
    
    # 2. 检查 Node.js 依赖
    nodejs_ok = check_nodejs_dependency()
    
    # 3. 如果环境变量正确，测试 SDK
    sdk_ok = False
    if env_ok:
        sdk_ok = await test_claude_sdk_basic()
    else:
        print("\n⏭️  跳过 SDK 测试，因为环境变量不完整")
    
    # 4. 总结
    print("\n" + "=" * 60)
    print("📊 验证结果总结")
    print("=" * 60)
    
    print(f"环境变量配置: {'✅ 正常' if env_ok else '❌ 异常'}")
    print(f"Node.js 依赖: {'✅ 正常' if nodejs_ok else '❌ 异常'}")
    print(f"Claude SDK 测试: {'✅ 正常' if sdk_ok else '❌ 异常'}")
    
    if env_ok and nodejs_ok and sdk_ok:
        print("\n🎉 所有验证通过！lovart.ai 环境配置正确。")
        
        # 保存验证结果供后续参考
        verification_result = {
            "timestamp": str(asyncio.get_event_loop().time()),
            "env_vars_ok": env_ok,
            "nodejs_ok": nodejs_ok,
            "sdk_ok": sdk_ok,
            "api_key_prefix": os.getenv("ANTHROPIC_API_KEY", "")[:10] if os.getenv("ANTHROPIC_API_KEY") else "",
            "base_url": os.getenv("ANTHROPIC_BASE_URL", "default")
        }
        
        print(f"\n💾 验证结果已记录，API密钥前缀: {verification_result['api_key_prefix']}...")
        return True
    else:
        print("\n❌ 存在配置问题，请根据上述提示修复后重新验证。")
        return False

if __name__ == "__main__":
    try:
        result = asyncio.run(main())
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  验证被用户取消")
        sys.exit(130)
    except Exception as e:
        print(f"\n\n❌ 验证过程中发生未预期的错误: {e}")
        sys.exit(1)


