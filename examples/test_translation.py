#!/usr/bin/env python3
"""
翻译质量测试工具
对比不同翻译方式的输出质量
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.translator import SmartTranslator, AITranslator


# 测试用例
TEST_SENTENCES = [
    "你好，我是雪莉。很高兴见到你！",
    "哎呀，你怎么来了？真是让我又惊又喜呢！",
    "今天天气真不错，我们出去玩吧！",
    "哼，才没有很想你呢。",
    "那个...谢谢你一直陪在我身边。",
    "喂！你在看哪里啊，笨蛋！",
]


async def test_translator(name: str, translator, target_lang: str = "ja"):
    """测试单个翻译器"""
    print(f"\n{'='*60}")
    print(f"🤖 测试: {name}")
    print(f"{'='*60}\n")
    
    if not translator.is_available():
        print("❌ 翻译器不可用\n")
        return
    
    for text in TEST_SENTENCES:
        print(f"原文: {text}")
        try:
            if asyncio.iscoroutinefunction(translator.translate):
                result = await translator.translate(text, target_lang)
            else:
                result = translator.translate(text, target_lang)
            print(f"译文: {result}\n")
        except Exception as e:
            print(f"❌ 错误: {e}\n")


async def compare_translators():
    """对比不同翻译器的效果"""
    print("📝 翻译质量对比测试")
    print("=" * 60)
    
    # 1. Google 翻译
    from src.core.translator import SimpleTranslator
    google = SimpleTranslator()
    await test_translator("Google 翻译", google)
    
    # 2. OpenAI 翻译
    import os
    if os.environ.get("OPENAI_API_KEY"):
        openai = AITranslator(
            provider="openai",
            api_key=os.environ.get("OPENAI_API_KEY"),
            model="gpt-4o-mini"
        )
        await test_translator("OpenAI (gpt-4o-mini)", openai)
    else:
        print("\n⚠️ 跳过 OpenAI 测试（未设置 OPENAI_API_KEY）")
    
    # 3. Claude 翻译
    if os.environ.get("ANTHROPIC_API_KEY"):
        claude = AITranslator(
            provider="claude",
            api_key=os.environ.get("ANTHROPIC_API_KEY")
        )
        await test_translator("Claude (claude-3-haiku)", claude)
    else:
        print("\n⚠️ 跳过 Claude 测试（未设置 ANTHROPIC_API_KEY）")
    
    # 4. Ollama 翻译
    try:
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.get("http://localhost:11434/api/tags") as resp:
                if resp.status == 200:
                    ollama = AITranslator(
                        provider="ollama",
                        model="qwen2.5:7b"
                    )
                    await test_translator("Ollama (qwen2.5:7b)", ollama)
    except:
        print("\n⚠️ 跳过 Ollama 测试（服务未启动）")


async def interactive_test():
    """交互式测试"""
    print("\n🎤 交互式翻译测试")
    print("输入中文，查看不同翻译器的输出")
    print("输入 'quit' 退出\n")
    
    import os
    
    # 初始化可用的翻译器
    translators = {}
    
    # Google
    from src.core.translator import SimpleTranslator
    translators["Google"] = SimpleTranslator()
    
    # OpenAI
    if os.environ.get("OPENAI_API_KEY"):
        translators["OpenAI"] = AITranslator(
            provider="openai",
            api_key=os.environ.get("OPENAI_API_KEY"),
            model="gpt-4o-mini"
        )
    
    while True:
        text = input("\n中文输入 > ").strip()
        if text.lower() in ("quit", "exit", "q"):
            break
        if not text:
            continue
        
        print()
        for name, translator in translators.items():
            if translator.is_available():
                try:
                    if asyncio.iscoroutinefunction(translator.translate):
                        result = await translator.translate(text, "ja")
                    else:
                        result = translator.translate(text, "ja")
                    print(f"[{name}]: {result}")
                except Exception as e:
                    print(f"[{name}]: ❌ 错误 - {e}")


async def main():
    """主函数"""
    print("翻译质量测试工具")
    print("=" * 60)
    print("\n1. 批量对比测试")
    print("2. 交互式测试")
    
    choice = input("\n选择 (1-2): ").strip()
    
    if choice == "1":
        await compare_translators()
    elif choice == "2":
        await interactive_test()
    else:
        print("无效选项")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n退出")
