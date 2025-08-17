#!/usr/bin/env python3
import os
import asyncio
from claude_code_sdk import ClaudeSDKClient, ClaudeCodeOptions

async def main():
    api_key = os.getenv("ANTHROPIC_AUTH_TOKEN") or os.getenv("ANTHROPIC_API_KEY")
    base_url = os.getenv("ANTHROPIC_BASE_URL")
    print(f"API key set: {bool(api_key)} | Base URL: {base_url}")

    options = ClaudeCodeOptions(system_prompt="连接测试", max_turns=1)
    async with ClaudeSDKClient(options=options) as client:
        await client.query("请回复: 连接成功")
        async for message in client.receive_response():
            if type(message).__name__ == "ResultMessage":
                print("OK")
                return

if __name__ == "__main__":
    asyncio.run(main())



