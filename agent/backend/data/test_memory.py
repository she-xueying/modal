# -*- coding: utf-8 -*-
import asyncio
import sys
sys.path.insert(0, r"D:\modal\modal\agent\backend")
from app.core.memory_service import _EXTRACT_PROMPT
from app.core.llm import llm_client

async def main():
    prompt = _EXTRACT_PROMPT.format(
        user_msg="我叫李雷，今年25岁，在上海做后端开发，平时喜欢用Go语言",
        assistant_msg="你好，李雷！很高兴认识你。25岁在上海做后端开发，还喜欢用Go语言，听起来很棒。",
    )
    resp = await llm_client.chat(
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0,
        max_tokens=512,
    )
    content = resp["choices"][0]["message"]["content"]
    print("=== RAW RESPONSE ===")
    print(content)

asyncio.run(main())