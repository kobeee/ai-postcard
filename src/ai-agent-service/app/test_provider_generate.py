#!/usr/bin/env python3
import asyncio
from coding_service.providers.claude_provider import ClaudeCodeProvider

async def main():
    provider = ClaudeCodeProvider()
    prompt = "请生成一个最简单的HTML页面，正文显示 OK 两个字。"
    session_id = "smoke_provider_001"
    async for event in provider.generate(prompt, session_id):
        t = event.get("type")
        if t == "status":
            print("STATUS:", event.get("content"))
        elif t == "analysis":
            print("ANALYSIS:", event.get("content", "")[:60])
        elif t == "code_generation":
            print("CODE_CHUNK:", len(event.get("content", "")))
        elif t == "complete":
            print("COMPLETE length:", len(event.get("final_code", "")))
            return
        elif t == "error":
            print("ERROR:", event.get("content"))
            return

if __name__ == "__main__":
    asyncio.run(main())



