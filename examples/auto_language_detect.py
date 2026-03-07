#!/usr/bin/env python3
"""
自动语言检测与语音切换演示
根据文本自动选择合适的语音
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from langdetect import detect
    LANGDETECT_AVAILABLE = True
except ImportError:
    LANGDETECT_AVAILABLE = False
    print("警告: 未安装 langdetect，使用简单检测规则")
    print("安装: pip install langdetect")

from src.core.tts_manager import get_tts_manager


def simple_lang_detect(text: str) -> str:
    """简单的语言检测规则（不需要外部库）"""
    # 日文假名范围
    hiragana = any('\u3040' <= c <= '\u309F' for c in text)
    katakana = any('\u30A0' <= c <= '\u30FF' for c in text)
    
    # 中文汉字范围（粗略）
    chinese = any('\u4E00' <= c <= '\u9FFF' for c in text)
    
    # 日文判断
    if hiragana or katakana:
        return "ja"
    
    # 中文判断
    if chinese:
        return "zh"
    
    # 默认为英文
    return "en"


def detect_language(text: str) -> str:
    """检测文本语言"""
    if LANGDETECT_AVAILABLE:
        try:
            lang = detect(text)
            # 映射到我们的语言代码
            lang_map = {
                "zh-cn": "zh",
                "zh-tw": "zh",
                "zh-hk": "zh",
                "ja": "ja",
                "en": "en",
            }
            return lang_map.get(lang, lang)
        except:
            return simple_lang_detect(text)
    else:
        return simple_lang_detect(text)


async def auto_speak(text: str, tts=None):
    """
    自动检测语言并播放
    
    Args:
        text: 要播放的文本
        tts: TTS 管理器实例（可选）
    """
    if tts is None:
        tts = get_tts_manager(preferred_provider="edge")
    
    # 检测语言
    lang = detect_language(text)
    
    # 切换到对应语言
    print(f"检测到语言: {lang}")
    tts.set_language(lang)
    
    # 播放
    print(f"播放: {text}")
    result = await tts.speak(text)
    
    if result.success:
        print(f"✅ 成功 ({result.duration_ms:.0f}ms)\n")
    else:
        print(f"❌ 错误: {result.error}\n")
    
    return result


async def main():
    """主函数"""
    print("自动语言检测演示")
    print("=" * 50)
    
    # 测试文本（多种语言）
    test_texts = [
        "你好，我是雪莉。这是中文。",
        "こんにちは、シェリーです。日本語です。",
        "Hello, I'm Sherry. This is English.",
        "今天天气很好。ありがとうございます。Thank you!",
    ]
    
    tts = get_tts_manager(preferred_provider="edge")
    
    for text in test_texts:
        await auto_speak(text, tts)
        await asyncio.sleep(0.5)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n用户取消")
