#!/usr/bin/env python3
"""
日文语音演示 - 带自动翻译功能
展示如何使用日文 TTS 功能和自动翻译
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.tts_manager import get_tts_manager


async def demo_auto_translate():
    """演示自动翻译功能"""
    print("=== 自动翻译功能演示 ===\n")
    
    tts = get_tts_manager(preferred_provider="edge")
    
    # 切换到日文模式（会自动启用翻译）
    print("切换到日文模式...")
    tts.set_language("ja")
    
    # 中文输入，自动翻译成日文
    chinese_texts = [
        "你好，我是雪莉。",
        "今天天气真不错呢！",
        "你喜欢什么样的音乐？",
        "很高兴认识你，希望我们能成为好朋友。",
    ]
    
    print("\n输入中文，自动翻译成日文播放：\n")
    for text in chinese_texts:
        print(f"中文输入: {text}")
        result = await tts.speak(text)
        if result.success:
            print(f"✅ 播放成功 ({result.duration_ms:.0f}ms)\n")
        else:
            print(f"❌ 错误: {result.error}\n")


async def demo_edge_tts_japanese():
    """演示 Edge TTS 日文语音"""
    print("=== Edge TTS 日文语音演示 ===\n")
    
    tts = get_tts_manager(preferred_provider="edge")
    
    # 禁用自动翻译，直接播放日文
    tts.set_auto_translate(False)
    print("已禁用自动翻译\n")
    
    # 设置日文语音
    tts.set_edge_voice("ja-JP-NanamiNeural")
    print("已切换到日文语音: ja-JP-NanamiNeural\n")
    
    # 测试日文文本
    japanese_texts = [
        "こんにちは、私はシェリーです。",
        "お元気ですか？今日も素晴らしい一日をお過ごしください。",
        "日本語の音声合成テストです。",
    ]
    
    for text in japanese_texts:
        print(f"日文输入: {text}")
        result = await tts.speak(text)
        if result.success:
            print(f"✅ 成功生成音频: {result.duration_ms:.0f}ms\n")
        else:
            print(f"❌ 错误: {result.error}\n")


async def demo_gptsovits_japanese():
    """演示 GPT-SoVITS 日文语音克隆"""
    print("=== GPT-SoVITS 日文语音克隆演示 ===\n")
    
    tts = get_tts_manager(preferred_provider="gptsovits")
    
    # 检查 GPT-SoVITS 是否可用
    if "gptsovits" not in tts.get_available_providers():
        print("⚠️ GPT-SoVITS 不可用，请确保：")
        print("1. 已部署 GPT-SoVITS 并启动 api_v2.py")
        print("2. config.yaml 中 enabled: true")
        return
    
    # 切换到日文模式（启用自动翻译）
    tts.set_language("ja")
    print("已切换到日文模式，自动翻译已启用\n")
    
    # 测试中文自动翻译成日文
    print("测试中文自动翻译：\n")
    test_texts = [
        "早上好！",
        "今天的心情很好。",
    ]
    
    for text in test_texts:
        print(f"中文: {text}")
        result = await tts.speak(text)
        if result.success:
            print(f"✅ 成功生成音频: {result.duration_ms:.0f}ms\n")
        else:
            print(f"❌ 错误: {result.error}\n")


async def demo_language_switching():
    """演示语言切换功能"""
    print("=== 多语言切换演示 ===\n")
    
    tts = get_tts_manager(preferred_provider="edge")
    
    # 测试不同语言
    test_cases = [
        ("zh", "你好，我是雪莉。这是中文语音测试。"),
        ("ja", "こんにちは、シェリーです。日本語のテストです。"),
        ("en", "Hello, I'm Sherry. This is an English voice test."),
    ]
    
    for lang, text in test_cases:
        print(f"切换到 {lang} 语言")
        tts.set_language(lang)
        print(f"播放: {text}")
        result = await tts.speak(text)
        if result.success:
            print(f"✅ 成功 ({result.duration_ms:.0f}ms)\n")
        else:
            print(f"❌ 错误: {result.error}\n")


async def main():
    """主函数"""
    print("日文语音功能演示（带自动翻译）")
    print("=" * 60)
    print("\n📌 提示：在日文模式下，中文会自动翻译成日文")
    
    # 选择演示模式
    print("\n选择演示模式:")
    print("1. 自动翻译功能（中文→日文）")
    print("2. Edge TTS 日文语音（直接日文输入）")
    print("3. GPT-SoVITS 日文语音克隆")
    print("4. 多语言切换")
    print("5. 全部演示")
    
    choice = input("\n请输入选项 (1-5): ").strip()
    
    try:
        if choice == "1":
            await demo_auto_translate()
        elif choice == "2":
            await demo_edge_tts_japanese()
        elif choice == "3":
            await demo_gptsovits_japanese()
        elif choice == "4":
            await demo_language_switching()
        elif choice == "5":
            await demo_auto_translate()
            print("\n" + "=" * 60 + "\n")
            await demo_edge_tts_japanese()
            print("\n" + "=" * 60 + "\n")
            await demo_gptsovits_japanese()
            print("\n" + "=" * 60 + "\n")
            await demo_language_switching()
        else:
            print("无效选项")
    except KeyboardInterrupt:
        print("\n\n用户取消")
    except Exception as e:
        print(f"\n错误: {e}")


if __name__ == "__main__":
    asyncio.run(main())
