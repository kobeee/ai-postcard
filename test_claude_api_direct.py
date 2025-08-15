#!/usr/bin/env python3
"""
直接测试Claude API的脚本
专门验证当前API密钥和URL的有效性
"""

import os
import sys
import requests
import json
from dotenv import load_dotenv

def test_claude_api_direct():
    """直接测试Claude API连接"""
    print("🚀 直接测试Claude API连接")
    print("=" * 50)
    
    # 加载环境变量
    load_dotenv()
    
    # 获取配置
    api_key = os.getenv("ANTHROPIC_API_KEY")
    base_url = os.getenv("ANTHROPIC_BASE_URL", "https://api.anthropic.com")
    
    if not api_key:
        print("❌ ANTHROPIC_API_KEY 未设置")
        return False
    
    print(f"📋 测试配置:")
    print(f"  API密钥: {api_key[:10]}...{api_key[-4:]}")
    print(f"  Base URL: {base_url}")
    
    # 测试messages端点
    url = f"{base_url}/v1/messages"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "anthropic-version": "2023-06-01"
    }
    
    payload = {
        "model": "claude-3-sonnet-20240229",
        "max_tokens": 100,
        "messages": [
            {
                "role": "user",
                "content": "Hello, can you hear me? Please respond with a simple 'Yes, I can hear you!'"
            }
        ]
    }
    
    print(f"\n🧪 测试请求:")
    print(f"  URL: {url}")
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        
        print(f"\n📊 响应结果:")
        print(f"  状态码: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"  ✅ 成功响应!")
            
            # 提取回复内容
            if 'content' in result and len(result['content']) > 0:
                content = result['content'][0]
                if 'text' in content:
                    print(f"  Claude回复: {content['text']}")
            
            return True
            
        elif response.status_code == 401:
            print(f"  ❌ 认证失败: {response.text}")
            return False
            
        else:
            print(f"  ⚠️  其他错误: {response.status_code}")
            print(f"  错误详情: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"  ❌ 请求异常: {e}")
        return False
    except Exception as e:
        print(f"  ❌ 其他异常: {e}")
        return False

def main():
    """主测试函数"""
    print("🔍 Claude API密钥和URL兼容性测试")
    print("=" * 60)
    
    # 测试环境变量
    load_dotenv()
    api_key = os.getenv("ANTHROPIC_API_KEY")
    base_url = os.getenv("ANTHROPIC_BASE_URL")
    
    print(f"📋 当前环境:")
    print(f"  API密钥: {'已设置' if api_key else '未设置'}")
    print(f"  Base URL: {base_url or '使用默认值'}")
    
    if not api_key:
        print("❌ 请先设置ANTHROPIC_API_KEY环境变量")
        return False
    
    # 测试messages端点
    messages_ok = test_claude_api_direct()
    
    print("\n📊 测试结果总结")
    print("=" * 30)
    print(f"  Messages端点: {'✅ 正常' if messages_ok else '❌ 异常'}")
    
    if messages_ok:
        print("🎉 测试通过！API密钥和URL配置正确")
        return True
    else:
        print("❌ 存在配置问题，需要检查API密钥和URL设置")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
