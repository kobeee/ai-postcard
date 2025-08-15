#!/usr/bin/env python3
"""
直接测试原生 Anthropic API 端点
绕过 Claude Code SDK 直接验证API密钥和URL
"""

import os
import json
import requests

def test_api():
    print("==== 直接测试 API 端点 ====")
    
    # 获取环境变量
    api_key = os.getenv("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_AUTH_TOKEN")
    base_url = os.getenv("ANTHROPIC_BASE_URL", "https://api.anthropic.com")
    
    if not api_key:
        print("❌ 未设置 API 密钥")
        return False
    
    print(f"🔑 API 密钥: {api_key[:10]}...{api_key[-4:]}")
    print(f"🔗 API URL: {base_url}")
    
    # 直接向 messages 端点发送请求
    # 尝试使用不同的URL路径
    print("\n🔍 尝试不同的API端点路径...")
    
    # 多个可能的API路径
    endpoints = [
        f"{base_url}/v1/messages",
        f"{base_url}/api/v1/messages",
        f"{base_url}/claude/v1/messages",
        f"{base_url}/v1/chat/completions",  # OpenAI兼容格式
        f"{base_url}/chat/completions",      # OpenAI兼容格式
        f"{base_url}"                        # 直接根路径
    ]
    
    print(f"将尝试以下端点：{', '.join(endpoints)}")
    
    headers = {
        "x-api-key": api_key,
        "Authorization": f"Bearer {api_key}", 
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }
    
    # 尝试两种不同格式的请求
    data_formats = [
        # Anthropic格式
        {
            "model": "claude-3-sonnet-20240229",
            "max_tokens": 100,
            "messages": [{"role": "user", "content": "Say OK"}]
        },
        # OpenAI格式
        {
            "model": "gpt-3.5-turbo",
            "max_tokens": 100,
            "messages": [{"role": "user", "content": "Say OK"}]
        }
    ]
    
    url = endpoints[0]  # 默认使用第一个端点
    
    print("\n📤 开始API测试...")
    
    # 系统地测试每个端点和请求格式的组合
    for endpoint in endpoints:
        print(f"\n🔍 测试端点: {endpoint}")
        
        for i, data_format in enumerate(data_formats):
            data_type = "Anthropic" if i == 0 else "OpenAI"
            print(f"  📋 使用{data_type}格式请求...")
            
            # 首先尝试x-api-key方式
            test_headers = {k:v for k,v in headers.items()}
            if "Authorization" in test_headers:
                del test_headers["Authorization"]
            
            try:
                print(f"  🔑 使用x-api-key认证...")
                response = requests.post(endpoint, headers=test_headers, json=data_format, timeout=10)
                print(f"  📥 状态码: {response.status_code}")
                
                # 尝试解析响应
                try:
                    if response.status_code == 200:
                        result = response.json()
                        print(f"  ✅ 成功! 响应为有效JSON!")
                        # 尝试提取内容
                        if "content" in result:
                            print(f"  💬 响应内容: {result['content'][0].get('text', '')[:100] if len(result['content']) > 0 else '空内容'}")
                            return True
                        elif "choices" in result:  # OpenAI格式
                            print(f"  💬 响应内容: {result['choices'][0].get('message', {}).get('content', '')[:100] if len(result['choices']) > 0 else '空内容'}")
                            return True
                        else:
                            print(f"  📄 响应结构: {json.dumps(result)[:200]}...")
                    elif 300 <= response.status_code < 400:
                        print(f"  ↪️ 重定向: {response.headers.get('Location', '未知')}")
                    else:
                        print(f"  📄 响应内容: {response.text[:200]}...")
                except ValueError:
                    print(f"  ⚠️ 响应不是有效JSON: {response.text[:200]}...")
                    # 检查是否为HTML页面
                    if "<html" in response.text.lower():
                        print("  📄 响应是HTML页面，可能是代理页面")
            except Exception as e:
                print(f"  ❌ 请求错误: {e}")
                
            # 然后尝试Bearer令牌方式
            test_headers = {k:v for k,v in headers.items() if k != "x-api-key"}
            try:
                print(f"  🔑 使用Bearer认证...")
                response = requests.post(endpoint, headers=test_headers, json=data_format, timeout=10)
                print(f"  📥 状态码: {response.status_code}")
                
                # 尝试解析响应
                try:
                    if response.status_code == 200:
                        result = response.json()
                        print(f"  ✅ 成功! 响应为有效JSON!")
                        # 尝试提取内容
                        if "content" in result:
                            print(f"  💬 响应内容: {result['content'][0].get('text', '')[:100] if len(result['content']) > 0 else '空内容'}")
                            return True
                        elif "choices" in result:  # OpenAI格式
                            print(f"  💬 响应内容: {result['choices'][0].get('message', {}).get('content', '')[:100] if len(result['choices']) > 0 else '空内容'}")
                            return True
                        else:
                            print(f"  📄 响应结构: {json.dumps(result)[:200]}...")
                    else:
                        print(f"  📄 响应内容: {response.text[:200]}...")
                except ValueError:
                    print(f"  ⚠️ 响应不是有效JSON: {response.text[:200]}...")
            except Exception as e:
                print(f"  ❌ 请求错误: {e}")
    
    # 尝试直接显示响应内容
    print("\n🔬 获取完整的原始响应...")
    try:
        url = f"{base_url}"
        response = requests.get(url, timeout=10)
        print(f"GET {url} 状态码: {response.status_code}")
        print(f"内容类型: {response.headers.get('content-type', '未知')}")
        print(f"内容前200字符: {response.text[:200]}...")
    except Exception as e:
        print(f"❌ 请求错误: {e}")
    
    return False

if __name__ == "__main__":
    test_api()
