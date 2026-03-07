#!/usr/bin/env python3
"""
国内翻译API测试工具
用于验证百度/有道/小牛翻译API是否配置正确
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.translator_china import BaiduTranslator, YoudaoTranslator, NiutransTranslator


TEST_TEXT = "很高兴认识你，希望我们能成为好朋友。"


async def test_baidu(app_id: str, app_key: str):
    """测试百度翻译"""
    print("\n" + "="*60)
    print("🧪 测试百度翻译")
    print("="*60)
    
    translator = BaiduTranslator(app_id=app_id, app_key=app_key)
    
    if not translator.is_available():
        print("❌ 未配置 API ID/Key")
        return
    
    print(f"原文: {TEST_TEXT}")
    
    try:
        result = await translator.translate(TEST_TEXT, target_lang="ja")
        print(f"译文: {result}")
        
        if result and result != TEST_TEXT:
            print("✅ 百度翻译测试通过！")
        else:
            print("⚠️ 返回了原文，可能有问题")
            
    except Exception as e:
        print(f"❌ 错误: {e}")
        print("\n常见问题：")
        print("- 52003: APP ID 或密钥错误")
        print("- 54003: 访问频率过高")
        print("- 58001: 余额不足或服务未开通")


async def test_youdao(app_id: str, app_key: str):
    """测试有道翻译"""
    print("\n" + "="*60)
    print("🧪 测试有道翻译")
    print("="*60)
    
    translator = YoudaoTranslator(app_id=app_id, app_key=app_key)
    
    if not translator.is_available():
        print("❌ 未配置 API ID/Key")
        return
    
    print(f"原文: {TEST_TEXT}")
    
    try:
        result = await translator.translate(TEST_TEXT, target_lang="ja")
        print(f"译文: {result}")
        
        if result and result != TEST_TEXT:
            print("✅ 有道翻译测试通过！")
        else:
            print("⚠️ 返回了原文，可能有问题")
            
    except Exception as e:
        print(f"❌ 错误: {e}")
        print("\n常见问题：")
        print("- 请检查控制台是否已开通"文本翻译"服务")


async def test_niutrans(api_key: str):
    """测试小牛翻译"""
    print("\n" + "="*60)
    print("🧪 测试小牛翻译")
    print("="*60)
    
    translator = NiutransTranslator(api_key=api_key)
    
    if not translator.is_available():
        print("❌ 未配置 API Key")
        return
    
    print(f"原文: {TEST_TEXT}")
    print(f"API Key: {api_key[:8]}...{api_key[-4:] if len(api_key) > 12 else ''}")
    
    try:
        result = await translator.translate(TEST_TEXT, target_lang="ja")
        print(f"译文: {result}")
        
        if result and result != TEST_TEXT:
            print("✅ 小牛翻译测试通过！")
        else:
            print("⚠️ 返回了原文，可能有问题")
            
    except Exception as e:
        print(f"❌ 错误: {e}")
        print("\n常见问题：")
        print("- 请访问 https://niutrans.com/documents/develop/develop_text/free 查看API文档")
        print("- 确认API Key已激活")
        print("- 检查控制台是否有余额或试用额度")


async def main():
    """主函数"""
    print("国内翻译API测试工具")
    print("="*60)
    print("\n此工具用于验证你的翻译API配置是否正确")
    print("测试前请确保已在 config.yaml 中配置API密钥\n")
    
    # 从配置文件读取
    try:
        import yaml
        config_path = Path(__file__).parent.parent / "config.yaml"
        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f) or {}
            
            translation_cfg = config.get("tts", {}).get("translation", {})
            china_cfg = translation_cfg.get("china", {})
            
            # 测试百度
            baidu_cfg = china_cfg.get("baidu", {})
            if baidu_cfg.get("app_id") and baidu_cfg.get("app_key"):
                await test_baidu(baidu_cfg["app_id"], baidu_cfg["app_key"])
            else:
                print("\n⚠️ 百度翻译未配置")
            
            # 测试有道
            youdao_cfg = china_cfg.get("youdao", {})
            if youdao_cfg.get("app_id") and youdao_cfg.get("app_key"):
                await test_youdao(youdao_cfg["app_id"], youdao_cfg["app_key"])
            else:
                print("\n⚠️ 有道翻译未配置")
            
            # 测试小牛
            niutrans_cfg = china_cfg.get("niutrans", {})
            if niutrans_cfg.get("api_key"):
                await test_niutrans(niutrans_cfg["api_key"])
            else:
                print("\n⚠️ 小牛翻译未配置")
            
        else:
            print("❌ 未找到 config.yaml 配置文件")
            
    except ImportError:
        print("请先安装 pyyaml: pip install pyyaml")
    except Exception as e:
        print(f"❌ 读取配置时出错: {e}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n退出")
