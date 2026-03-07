#!/usr/bin/env python3
"""
国内翻译API支持
- 百度翻译
- 有道翻译
- 腾讯翻译（待实现）
- 火山引擎翻译（待实现）

这些API在国内访问速度快，稳定性好
"""

import json
import hashlib
import random
import asyncio
from typing import Optional, Dict, Any
from urllib.parse import quote
import aiohttp
from loguru import logger


class BaiduTranslator:
    """
    百度翻译API
    文档: https://fanyi-api.baidu.com/
    免费额度: 标准版每月5万字符，高级版每月200万字符
    """
    
    API_URL = "https://fanyi-api.baidu.com/api/trans/vip/translate"
    
    def __init__(self, app_id: Optional[str] = None, app_key: Optional[str] = None):
        """
        初始化百度翻译
        
        Args:
            app_id: 百度翻译APP ID
            app_key: 百度翻译密钥
        """
        self.app_id = app_id
        self.app_key = app_key
        self._initialized = bool(app_id and app_key)
        
        if self._initialized:
            logger.info("✅ Baidu translator initialized")
        else:
            logger.debug("⚠️ Baidu translator not configured (missing app_id/app_key)")
    
    def is_available(self) -> bool:
        return self._initialized
    
    def _generate_sign(self, query: str, salt: str) -> str:
        """生成百度翻译签名"""
        # 签名: appid + q + salt + 密钥 的MD5值
        sign_str = f"{self.app_id}{query}{salt}{self.app_key}"
        return hashlib.md5(sign_str.encode('utf-8')).hexdigest()
    
    async def translate(self, text: str, target_lang: str = "ja", source_lang: str = "auto") -> str:
        """
        使用百度翻译
        
        Args:
            text: 要翻译的文本
            target_lang: 目标语言 (zh, en, jp, kor, fra, spa, th, ara, ru, pt, de, it, el, nl, pl, bul, est, dan, fin, cs, rom, slo, swe, hu, cht, vie)
            source_lang: 源语言 (auto 表示自动检测)
        
        Returns:
            翻译后的文本
        """
        if not self._initialized or not text or not text.strip():
            return text
        
        # 语言代码映射
        lang_map = {
            "ja": "jp",      # 日语
            "zh": "zh",      # 中文
            "en": "en",      # 英语
            "ko": "kor",     # 韩语
            "fr": "fra",     # 法语
            "es": "spa",     # 西班牙语
            "th": "th",      # 泰语
            "ar": "ara",     # 阿拉伯语
            "ru": "ru",      # 俄语
            "de": "de",      # 德语
        }
        
        target = lang_map.get(target_lang, target_lang)
        source = "auto" if source_lang == "auto" else lang_map.get(source_lang, source_lang)
        
        # 生成随机salt
        salt = str(random.randint(32768, 65536))
        sign = self._generate_sign(text, salt)
        
        params = {
            "q": text,
            "from": source,
            "to": target,
            "appid": self.app_id,
            "salt": salt,
            "sign": sign,
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.API_URL, params=params, timeout=10) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(f"Baidu API error {response.status}: {error_text}")
                    
                    result = await response.json()
                    
                    if "error_code" in result:
                        error_msg = result.get("error_msg", "Unknown error")
                        raise Exception(f"Baidu API error {result['error_code']}: {error_msg}")
                    
                    # 拼接翻译结果
                    translations = result.get("trans_result", [])
                    translated = " ".join([item.get("dst", "") for item in translations])
                    
                    logger.info(f"🇨🇳 百度翻译: '{text[:40]}...' -> '{translated[:40]}...'")
                    return translated
                    
        except Exception as e:
            logger.error(f"❌ Baidu translation failed: {e}")
            return text


class YoudaoTranslator:
    """
    有道翻译API
    文档: https://ai.youdao.com/doc.s#guide
    免费额度: 新用户赠送50元体验金
    """
    
    API_URL = "https://openapi.youdao.com/api"
    
    def __init__(self, app_id: Optional[str] = None, app_key: Optional[str] = None):
        """
        初始化有道翻译
        
        Args:
            app_id: 有道智云APP ID
            app_key: 有道智云应用密钥
        """
        self.app_id = app_id
        self.app_key = app_key
        self._initialized = bool(app_id and app_key)
        
        if self._initialized:
            logger.info("✅ Youdao translator initialized")
        else:
            logger.debug("⚠️ Youdao translator not configured (missing app_id/app_key)")
    
    def is_available(self) -> bool:
        return self._initialized
    
    def _generate_sign(self, query: str, salt: str, curtime: str) -> str:
        """生成有道翻译签名"""
        # 签名: sha256(应用ID + input + salt + curtime + 应用密钥)
        # input: 如果query长度<=20，则input=query; 否则input=query前10+长度+query后10
        if len(query) <= 20:
            input_str = query
        else:
            input_str = query[:10] + str(len(query)) + query[-10:]
        
        sign_str = f"{self.app_id}{input_str}{salt}{curtime}{self.app_key}"
        return hashlib.sha256(sign_str.encode('utf-8')).hexdigest()
    
    async def translate(self, text: str, target_lang: str = "ja", source_lang: str = "auto") -> str:
        """
        使用有道翻译
        
        Args:
            text: 要翻译的文本
            target_lang: 目标语言 (zh-CHS, zh-CHT, en, ja, ko, fr, es, pt, it, ru, vi, de, ar, id)
            source_lang: 源语言 (auto 表示自动检测)
        
        Returns:
            翻译后的文本
        """
        if not self._initialized or not text or not text.strip():
            return text
        
        # 语言代码映射
        lang_map = {
            "ja": "ja",
            "zh": "zh-CHS",
            "en": "en",
            "ko": "ko",
            "fr": "fr",
            "es": "es",
            "de": "de",
            "ru": "ru",
        }
        
        target = lang_map.get(target_lang, target_lang)
        source = "auto" if source_lang == "auto" else lang_map.get(source_lang, source_lang)
        
        # 生成参数
        salt = str(random.randint(1, 65536))
        curtime = str(int(asyncio.get_event_loop().time()))
        sign = self._generate_sign(text, salt, curtime)
        
        data = {
            "q": text,
            "from": source,
            "to": target,
            "appKey": self.app_id,
            "salt": salt,
            "sign": sign,
            "signType": "v3",
            "curtime": curtime,
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.API_URL, data=data, timeout=10) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(f"Youdao API error {response.status}: {error_text}")
                    
                    result = await response.json()
                    
                    if result.get("errorCode") != "0":
                        error_msg = result.get("errorMsg", "Unknown error")
                        raise Exception(f"Youdao API error {result['errorCode']}: {error_msg}")
                    
                    # 获取翻译结果
                    translations = result.get("translation", [])
                    if translations:
                        translated = translations[0]
                        logger.info(f"🇨🇳 有道翻译: '{text[:40]}...' -> '{translated[:40]}...'")
                        return translated
                    else:
                        return text
                    
        except Exception as e:
            logger.error(f"❌ Youdao translation failed: {e}")
            return text


class NiutransTranslator:
    """
    小牛翻译（东北大学）
    文档: https://niutrans.com/documents/develop/develop_text/free
    免费额度: 每天20万字符
    """
    
    API_URL = "https://api.niutrans.com/NiuTransServer/translation"
    
    def __init__(self, api_key: Optional[str] = None):
        """
        初始化小牛翻译
        
        Args:
            api_key: 小牛翻译API密钥
        """
        self.api_key = api_key
        self._initialized = bool(api_key)
        
        if self._initialized:
            logger.info("✅ Niutrans translator initialized")
        else:
            logger.debug("⚠️ Niutrans translator not configured (missing api_key)")
    
    def is_available(self) -> bool:
        return self._initialized
    
    async def translate(self, text: str, target_lang: str = "ja", source_lang: str = "auto") -> str:
        """
        使用小牛翻译
        
        Args:
            text: 要翻译的文本
            target_lang: 目标语言 (zh, en, ja, ko, de, fr, ru, es, pt, it, ar, etc)
            source_lang: 源语言 (auto 表示自动检测)
        
        Returns:
            翻译后的文本
        """
        if not self._initialized or not text or not text.strip():
            return text
        
        # 小牛支持的语言代码与标准代码相同
        target = target_lang
        source = source_lang
        
        # 构建请求数据 - 小牛翻译需要用 POST 发送 JSON
        data = {
            "from": source,
            "to": target,
            "apikey": self.api_key,
            "src_text": text,
        }
        
        try:
            # 设置请求头
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
            
            async with aiohttp.ClientSession() as session:
                # 使用 POST 发送 JSON 数据
                async with session.post(
                    self.API_URL, 
                    json=data,  # 发送 JSON 格式
                    headers=headers,
                    timeout=10
                ) as response:
                    # 读取原始响应文本
                    response_text = await response.text()
                    
                    # 检查是否返回了HTML错误页面（通常是认证或配置问题）
                    if response_text.strip().startswith('<!DOCTYPE') or response_text.strip().startswith('<html'):
                        logger.warning(f"⚠️ 小牛翻译返回了HTML页面，可能是API密钥无效或服务未激活")
                        logger.debug(f"响应内容: {response_text[:500]}")
                        raise Exception(
                            f"小牛翻译API认证失败。请检查:\n"
                            f"1. API密钥是否正确: {self.api_key[:8]}...\n"
                            f"2. 是否已在控制台激活服务\n"
                            f"3. 账户是否有余额或试用额度\n"
                            f"控制台: https://niutrans.com/"
                        )
                    
                    if response.status != 200:
                        raise Exception(f"Niutrans API HTTP {response.status}: {response_text[:200]}")
                    
                    # 尝试解析 JSON
                    try:
                        result = json.loads(response_text)
                    except json.JSONDecodeError:
                        logger.error(f"Niutrans returned non-JSON: {response_text[:500]}")
                        raise Exception(f"Invalid JSON response from Niutrans")
                    
                    # 检查错误码
                    if result.get("error_code") and result.get("error_code") != "0":
                        error_msg = result.get("error_msg", "Unknown error")
                        raise Exception(f"Niutrans API error {result['error_code']}: {error_msg}")
                    
                    translated = result.get("tgt_text", text)
                    if translated and translated != text:
                        logger.info(f"🇨🇳 小牛翻译: '{text[:40]}...' -> '{translated[:40]}...'")
                    return translated or text
                    
        except Exception as e:
            logger.error(f"❌ Niutrans translation failed: {e}")
            return text


class ChinaTranslatorManager:
    """
    国内翻译管理器
    自动选择可用的国内翻译API
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化国内翻译管理器
        
        Args:
            config: 配置字典，包含各翻译API的密钥
        """
        config = config or {}
        
        # 初始化各个翻译器
        self.translators = []
        
        # 百度翻译
        baidu_config = config.get("baidu", {})
        if baidu_config.get("app_id") and baidu_config.get("app_key"):
            self.translators.append(BaiduTranslator(
                app_id=baidu_config.get("app_id"),
                app_key=baidu_config.get("app_key")
            ))
        
        # 有道翻译
        youdao_config = config.get("youdao", {})
        if youdao_config.get("app_id") and youdao_config.get("app_key"):
            self.translators.append(YoudaoTranslator(
                app_id=youdao_config.get("app_id"),
                app_key=youdao_config.get("app_key")
            ))
        
        # 小牛翻译
        niutrans_config = config.get("niutrans", {})
        if niutrans_config.get("api_key"):
            self.translators.append(NiutransTranslator(
                api_key=niutrans_config.get("api_key")
            ))
        
        # 筛选可用的翻译器
        self.available_translators = [t for t in self.translators if t.is_available()]
        
        if self.available_translators:
            names = [t.__class__.__name__.replace("Translator", "") for t in self.available_translators]
            logger.info(f"✅ 国内翻译API可用: {', '.join(names)}")
        else:
            logger.info("⚠️ 未配置国内翻译API")
    
    def is_available(self) -> bool:
        """检查是否有可用的翻译器"""
        return len(self.available_translators) > 0
    
    async def translate(self, text: str, target_lang: str = "ja", source_lang: str = "auto") -> str:
        """
        使用国内API翻译
        按顺序尝试各个翻译器，直到成功
        
        Args:
            text: 要翻译的文本
            target_lang: 目标语言
            source_lang: 源语言
        
        Returns:
            翻译后的文本
        """
        if not self.available_translators:
            return text
        
        # 尝试各个翻译器
        for translator in self.available_translators:
            try:
                result = await translator.translate(text, target_lang, source_lang)
                if result and result != text:
                    return result
            except Exception as e:
                logger.warning(f"{translator.__class__.__name__} failed: {e}")
                continue
        
        # 全部失败，返回原文
        return text
