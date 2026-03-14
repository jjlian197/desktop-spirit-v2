#!/usr/bin/env python3
"""
Translator - 高质量翻译模块
支持 DeepL API (推荐)、Google Translate (备用)
"""

import os
import json
import asyncio
from abc import ABC, abstractmethod
from typing import Optional, Dict
from dataclasses import dataclass
from pathlib import Path

from loguru import logger


@dataclass
class TranslationResult:
    """翻译结果"""
    text: str
    source_lang: str
    target_lang: str
    success: bool
    error: Optional[str] = None


class BaseTranslator(ABC):
    """翻译器基类"""
    
    @abstractmethod
    async def translate(self, text: str, target_lang: str, source_lang: str = "auto") -> TranslationResult:
        """翻译文本"""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """检查是否可用"""
        pass


class BaiduTranslator(BaseTranslator):
    """
    百度翻译 API (推荐 - 国内最稳定)
    - 标准版: 每月5万字符免费
    - 高级版: 每月100万字符免费
    - 官网: https://fanyi-api.baidu.com/
    - 特点: 国内访问快，中日翻译质量较好
    """
    
    API_URL = "https://fanyi-api.baidu.com/api/trans/vip/translate"
    
    # 百度语言代码
    LANG_MAP = {
        "zh": "zh",      # 中文
        "jp": "jp",      # 日语
        "ja": "jp",      # 日语 (标准代码)
        "en": "en",      # 英语
    }
    
    def __init__(self, app_id: Optional[str] = None, app_key: Optional[str] = None):
        self.app_id = app_id or os.environ.get("BAIDU_APP_ID", "")
        self.app_key = app_key or os.environ.get("BAIDU_APP_KEY", "")
        self._initialized = bool(self.app_id and self.app_key)
        if self._initialized:
            logger.info("✅ Baidu Translator 已初始化")
    
    def is_available(self) -> bool:
        return self._initialized
    
    def _make_sign(self, query: str, salt: str) -> str:
        """生成百度 API 签名"""
        import hashlib
        sign_str = self.app_id + query + salt + self.app_key
        return hashlib.md5(sign_str.encode('utf-8')).hexdigest()
    
    async def translate(self, text: str, target_lang: str, source_lang: str = "auto") -> TranslationResult:
        """使用百度翻译 API"""
        if not self._initialized:
            return TranslationResult(text, source_lang, target_lang, False, "百度翻译 API 未配置")
        
        target_code = self.LANG_MAP.get(target_lang, target_lang)
        source_code = self.LANG_MAP.get(source_lang, source_lang) if source_lang != "auto" else "auto"
        
        try:
            import aiohttp
            import random
            
            salt = str(random.randint(32768, 65536))
            sign = self._make_sign(text, salt)
            
            params = {
                "q": text,
                "from": source_code,
                "to": target_code,
                "appid": self.app_id,
                "salt": salt,
                "sign": sign,
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(self.API_URL, params=params) as resp:
                    result = await resp.json()
                    
                    if "error_code" in result:
                        error_msg = result.get("error_msg", "未知错误")
                        raise Exception(f"百度 API 错误 {result['error_code']}: {error_msg}")
                    
                    # 提取翻译结果
                    translated_parts = []
                    for item in result.get("trans_result", []):
                        translated_parts.append(item.get("dst", ""))
                    
                    translated = "".join(translated_parts)
                    
                    logger.debug(f"🌐 百度翻译: {text[:20]}... -> {translated[:20]}...")
                    
                    return TranslationResult(
                        text=translated,
                        source_lang=source_code,
                        target_lang=target_lang,
                        success=True
                    )
                    
        except Exception as e:
            logger.error(f"❌ 百度翻译失败: {e}")
            return TranslationResult(text, source_lang, target_lang, False, str(e))


class DeepLTranslator(BaseTranslator):
    """
    DeepL API 翻译器 (备选 - 质量最高)
    - 中日互译准确率业界领先
    - 免费版: 每月50万字符
    - 官网: https://www.deepl.com/pro-api
    """
    
    API_URL = "https://api-free.deepl.com/v2/translate"
    
    # 语言代码映射 (DeepL 格式)
    LANG_MAP = {
        "zh": "ZH",      # 中文
        "jp": "JA",      # 日语
        "ja": "JA",      # 日语 (标准代码)
        "en": "EN-US",   # 英语 (美国)
    }
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("DEEPL_API_KEY", "")
        self._initialized = bool(self.api_key)
        if self._initialized:
            logger.info("✅ DeepL Translator 已初始化")
    
    def is_available(self) -> bool:
        return self._initialized
    
    async def translate(self, text: str, target_lang: str, source_lang: str = "auto") -> TranslationResult:
        """使用 DeepL API 翻译"""
        if not self._initialized:
            return TranslationResult(text, source_lang, target_lang, False, "DeepL API Key 未设置")
        
        target_code = self.LANG_MAP.get(target_lang, target_lang.upper())
        source_code = self.LANG_MAP.get(source_lang, source_lang.upper()) if source_lang != "auto" else None
        
        try:
            import aiohttp
            
            headers = {
                "Authorization": f"DeepL-Auth-Key {self.api_key}",
                "Content-Type": "application/x-www-form-urlencoded"
            }
            
            data = {
                "text": text,
                "target_lang": target_code,
            }
            
            if source_code:
                data["source_lang"] = source_code
            
            async with aiohttp.ClientSession() as session:
                async with session.post(self.API_URL, headers=headers, data=data) as resp:
                    if resp.status != 200:
                        error_text = await resp.text()
                        raise Exception(f"DeepL API 错误 ({resp.status}): {error_text}")
                    
                    result = await resp.json()
                    translated = result["translations"][0]["text"]
                    detected_source = result["translations"][0].get("detected_source_language", source_lang)
                    
                    logger.debug(f"🌐 DeepL 翻译: {text[:20]}... -> {translated[:20]}...")
                    
                    return TranslationResult(
                        text=translated,
                        source_lang=detected_source,
                        target_lang=target_lang,
                        success=True
                    )
                    
        except Exception as e:
            logger.error(f"❌ DeepL 翻译失败: {e}")
            return TranslationResult(text, source_lang, target_lang, False, str(e))


class GoogleTranslator(BaseTranslator):
    """
    Google Translate (备用 - 无需API Key)
    使用 googletrans 库 (免费但可能不稳定)
    """
    
    LANG_MAP = {
        "zh": "zh-cn",
        "jp": "ja",
        "ja": "ja",
        "en": "en",
    }
    
    def __init__(self):
        self._initialized = False
        try:
            from googletrans import Translator
            self._translator = Translator()
            self._initialized = True
            logger.info("✅ Google Translator 已初始化")
        except ImportError:
            logger.warning("⚠️ googletrans 未安装，Google 翻译不可用")
    
    def is_available(self) -> bool:
        return self._initialized
    
    async def translate(self, text: str, target_lang: str, source_lang: str = "auto") -> TranslationResult:
        """使用 Google Translate 翻译"""
        if not self._initialized:
            return TranslationResult(text, source_lang, target_lang, False, "Google Translator 未初始化")
        
        target_code = self.LANG_MAP.get(target_lang, target_lang)
        source_code = self.LANG_MAP.get(source_lang, source_lang) if source_lang != "auto" else "auto"
        
        try:
            # 🚨 googletrans 4.0+ 是异步库，需要 await
            result = await self._translator.translate(text, dest=target_code, src=source_code)
            
            logger.debug(f"🌐 Google 翻译: {text[:20]}... -> {result.text[:20]}...")
            
            return TranslationResult(
                text=result.text,
                source_lang=result.src,
                target_lang=target_lang,
                success=True
            )
            
        except Exception as e:
            logger.error(f"❌ Google 翻译失败: {e}")
            return TranslationResult(text, source_lang, target_lang, False, str(e))


class TranslatorManager:
    """
    翻译管理器 - 自动选择最佳翻译引擎
    优先级: DeepL > Google
    """
    
    def __init__(self):
        self.translators: Dict[str, BaseTranslator] = {
            "baidu": BaiduTranslator(),     # 首选: 百度 (国内稳定)
            "google": GoogleTranslator(),    # 备用1: Google (免费)
            "deepl": DeepLTranslator(),      # 备用2: DeepL (高质量)
        }
        self.current_translator = self._select_translator()
        
        # 翻译缓存 (避免重复翻译相同内容)
        self._cache: Dict[str, str] = {}
        self._cache_enabled = True
        
        logger.info(f"🌐 TranslatorManager 初始化完成，使用: {self.current_translator.__class__.__name__}")
    
    def _select_translator(self) -> BaseTranslator:
        """选择最佳可用翻译器 (优先百度，国内最稳定)"""
        # 首选: 百度翻译 (国内速度快，质量较好)
        if self.translators["baidu"].is_available():
            logger.info("🌐 使用百度翻译作为翻译引擎")
            return self.translators["baidu"]
        
        # 备用1: Google (免费，无需 API Key)
        if self.translators["google"].is_available():
            logger.info("🌐 使用 Google 翻译作为翻译引擎")
            return self.translators["google"]
        
        # 备用2: DeepL (需要 API Key，但质量最高)
        if self.translators["deepl"].is_available():
            logger.info("🌐 使用 DeepL 作为翻译引擎")
            return self.translators["deepl"]
        
        # 都没有就返回 None (会原样返回文本)
        logger.warning("⚠️ 没有可用的翻译引擎")
        return None
    
    async def translate(self, text: str, target_lang: str, source_lang: str = "zh") -> str:
        """
        翻译文本，失败时返回原文
        
        Args:
            text: 要翻译的文本
            target_lang: 目标语言 (zh/jp/ja)
            source_lang: 源语言 (默认中文)
        
        Returns:
            翻译后的文本，失败返回原文
        """
        if not text or not text.strip():
            return text
        
        # 如果目标语言是中文，直接返回
        if target_lang in ("zh", "zh-cn"):
            return text
        
        # 检查缓存
        cache_key = f"{text}:{target_lang}"
        if self._cache_enabled and cache_key in self._cache:
            logger.debug(f"🌐 使用缓存翻译: {text[:20]}...")
            return self._cache[cache_key]
        
        # 没有翻译器可用，返回原文
        if self.current_translator is None:
            logger.warning("⚠️ 翻译器不可用，返回原文")
            return text
        
        # 执行翻译
        result = await self.current_translator.translate(text, target_lang, source_lang)
        
        if result.success:
            # 存入缓存
            if self._cache_enabled:
                self._cache[cache_key] = result.text
            return result.text
        else:
            logger.warning(f"⚠️ 翻译失败，返回原文: {result.error}")
            return text
    
    def translate_sync(self, text: str, target_lang: str, source_lang: str = "zh") -> str:
        """同步版本的翻译"""
        try:
            return asyncio.run(self.translate(text, target_lang, source_lang))
        except Exception as e:
            logger.error(f"❌ 同步翻译失败: {e}")
            return text
    
    def clear_cache(self):
        """清空翻译缓存"""
        self._cache.clear()
        logger.info("🌐 翻译缓存已清空")
    
    def get_status(self) -> dict:
        """获取翻译器状态"""
        return {
            "current": self.current_translator.__class__.__name__ if self.current_translator else "None",
            "baidu_available": self.translators["baidu"].is_available(),
            "google_available": self.translators["google"].is_available(),
            "deepl_available": self.translators["deepl"].is_available(),
            "cache_size": len(self._cache),
        }


# 单例
_translator_manager: Optional[TranslatorManager] = None


def get_translator() -> TranslatorManager:
    """获取翻译管理器单例"""
    global _translator_manager
    if _translator_manager is None:
        _translator_manager = TranslatorManager()
    return _translator_manager
