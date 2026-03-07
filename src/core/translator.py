#!/usr/bin/env python3
"""
翻译模块 - 支持多种高质量翻译方式
1. AI 翻译（OpenAI/Claude/Ollama）- 推荐，理解上下文
2. 本地翻译（适用于离线场景）
3. 缓存机制，避免重复翻译
"""

import re
import json
import hashlib
from typing import Optional, Dict, Any
from pathlib import Path
from dataclasses import dataclass
from loguru import logger


@dataclass
class TranslationCache:
    """翻译缓存"""
    cache_file: str = ".translation_cache.json"
    
    def __post_init__(self):
        self._cache: Dict[str, str] = {}
        self._load_cache()
    
    def _get_key(self, text: str, target_lang: str) -> str:
        """生成缓存键"""
        return hashlib.md5(f"{text}:{target_lang}".encode()).hexdigest()
    
    def _load_cache(self):
        """加载缓存"""
        try:
            cache_path = Path(self.cache_file)
            if cache_path.exists():
                with open(cache_path, 'r', encoding='utf-8') as f:
                    self._cache = json.load(f)
        except Exception as e:
            logger.debug(f"翻译缓存加载失败: {e}")
            self._cache = {}
    
    def _save_cache(self):
        """保存缓存"""
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self._cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.debug(f"翻译缓存保存失败: {e}")
    
    def get(self, text: str, target_lang: str) -> Optional[str]:
        """获取缓存的翻译"""
        key = self._get_key(text, target_lang)
        return self._cache.get(key)
    
    def set(self, text: str, target_lang: str, translation: str):
        """保存翻译到缓存"""
        key = self._get_key(text, target_lang)
        self._cache[key] = translation
        self._save_cache()


class AITranslator:
    """
    AI 翻译器（高质量）
    支持 OpenAI、Claude、本地模型等
    """
    
    def __init__(self, 
                 provider: str = "openai",
                 api_key: Optional[str] = None,
                 api_base: Optional[str] = None,
                 model: Optional[str] = None):
        """
        初始化 AI 翻译器
        
        Args:
            provider: "openai", "claude", "ollama"
            api_key: API 密钥
            api_base: API 基础地址（用于本地模型或代理）
            model: 模型名称
        """
        self.provider = provider.lower()
        self.api_key = api_key
        self.api_base = api_base
        self.model = model or self._default_model()
        
        # 初始化客户端
        self._client = None
        self._init_client()
    
    def _default_model(self) -> str:
        """获取默认模型"""
        defaults = {
            "openai": "gpt-4o-mini",  # 便宜且质量高
            "claude": "claude-3-haiku-20240307",
            "ollama": "qwen2.5:7b",  # 本地模型，可自行更换
        }
        return defaults.get(self.provider, "gpt-4o-mini")
    
    def _init_client(self):
        """初始化 API 客户端"""
        try:
            if self.provider == "openai":
                import openai
                self._client = openai.AsyncOpenAI(
                    api_key=self.api_key,
                    base_url=self.api_base
                )
                logger.info(f"✅ OpenAI translator initialized (model: {self.model})")
                
            elif self.provider == "claude":
                import anthropic
                self._client = anthropic.AsyncAnthropic(api_key=self.api_key)
                logger.info(f"✅ Claude translator initialized (model: {self.model})")
                
            elif self.provider == "ollama":
                # Ollama 不需要特殊客户端，使用 HTTP 请求
                self.api_base = self.api_base or "http://localhost:11434"
                logger.info(f"✅ Ollama translator initialized (model: {self.model})")
                
            else:
                logger.warning(f"⚠️ Unknown provider: {self.provider}")
                
        except ImportError as e:
            logger.warning(f"⚠️ Failed to init {self.provider} translator: {e}")
            self._client = None
        except Exception as e:
            logger.warning(f"⚠️ Failed to init {self.provider} translator: {e}")
            self._client = None
    
    def is_available(self) -> bool:
        """检查翻译器是否可用"""
        if self.provider == "ollama":
            return True  # Ollama 不依赖 API key
        return self._client is not None
    
    def _build_prompt(self, text: str, target_lang: str) -> str:
        """构建翻译提示词"""
        prompts = {
            "ja": """你是一个专业的中日翻译助手。请将以下中文翻译成自然流畅的日文。

要求：
1. 使用日常口语化的表达，适合语音合成（TTS）
2. 保留角色原有的语气和情感
3. 不要直译，要意译，让日文听起来自然
4. 如果是简短的问候或对话，使用女性化的温柔语气（です/ます调）
5. 只返回翻译结果，不要解释

中文：{text}

日文：""",
            "zh": """请将以下日文翻译成中文。

要求：
1. 保留原文的语气和情感
2. 自然流畅，不要生硬
3. 只返回翻译结果

日文：{text}

中文：""",
            "en": """Translate the following text to English.

Requirements:
1. Natural and fluent, suitable for TTS
2. Keep the original tone and emotion
3. Return only the translation

Text: {text}

English:"""
        }
        
        return prompts.get(target_lang, prompts["en"]).format(text=text)
    
    async def translate(self, text: str, target_lang: str = "ja") -> str:
        """
        使用 AI 翻译
        
        Args:
            text: 要翻译的文本
            target_lang: 目标语言
            
        Returns:
            翻译后的文本
        """
        if not text or not text.strip():
            return text
        
        if not self.is_available():
            logger.warning("AI translator not available, returning original text")
            return text
        
        prompt = self._build_prompt(text, target_lang)
        
        try:
            if self.provider == "openai":
                response = await self._client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "你是一个专业的翻译助手，擅长将文本翻译成自然流畅的目标语言。"},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.3,
                    max_tokens=500
                )
                translated = response.choices[0].message.content.strip()
                
            elif self.provider == "claude":
                response = await self._client.messages.create(
                    model=self.model,
                    max_tokens=500,
                    temperature=0.3,
                    system="你是一个专业的翻译助手，擅长将文本翻译成自然流畅的目标语言。",
                    messages=[{"role": "user", "content": prompt}]
                )
                translated = response.content[0].text.strip()
                
            elif self.provider == "ollama":
                import aiohttp
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        f"{self.api_base}/api/generate",
                        json={
                            "model": self.model,
                            "prompt": prompt,
                            "stream": False,
                            "options": {"temperature": 0.3}
                        }
                    ) as resp:
                        result = await resp.json()
                        translated = result.get("response", "").strip()
            else:
                return text
            
            # 清理结果
            translated = self._clean_result(translated, target_lang)
            
            logger.info(f"🤖 AI 翻译 ({self.provider}): '{text[:40]}...' -> '{translated[:40]}...'")
            return translated
            
        except Exception as e:
            logger.error(f"❌ AI translation failed: {e}")
            return text
    
    def _clean_result(self, text: str, target_lang: str) -> str:
        """清理翻译结果"""
        # 去除常见的提示词残留
        prefixes = ["日文：", "日本語：", "中文：", "English:", "翻译：", "译文："]
        for prefix in prefixes:
            if text.startswith(prefix):
                text = text[len(prefix):].strip()
        
        # 去除引号
        text = text.strip('"\'"""''')
        
        return text


class SimpleTranslator:
    """
    简单翻译器（备用）
    使用 Google 翻译作为后备
    """
    
    def __init__(self):
        self._translator = None
        self._initialized = False
        self._init_translator()
    
    def _init_translator(self):
        """初始化翻译器"""
        try:
            from deep_translator import GoogleTranslator
            self._translator = GoogleTranslator(source='auto', target='ja')
            self._initialized = True
            logger.info("✅ Google translator initialized (backup)")
        except ImportError:
            logger.debug("⚠️ deep-translator not installed")
        except Exception as e:
            logger.debug(f"⚠️ Google translator init failed: {e}")
    
    def is_available(self) -> bool:
        return self._initialized
    
    async def translate(self, text: str, target_lang: str = "ja") -> str:
        """翻译文本"""
        if not self._initialized or not text or not text.strip():
            return text
        
        try:
            self._translator.target = target_lang
            translated = self._translator.translate(text)
            logger.debug(f"Google 翻译: '{text[:40]}...' -> '{translated[:40]}...'")
            return translated
        except Exception as e:
            logger.warning(f"Google translation failed: {e}")
            return text


class SmartTranslator:
    """
    智能翻译器（推荐使用）
    翻译优先级：
    1. AI 翻译（OpenAI/Claude/Ollama）- 最高质量
    2. 国内翻译 API（百度/有道/小牛）- 国内访问快
    3. Google 翻译 - 免费备选
    带缓存机制
    """
    
    def __init__(self, 
                 ai_provider: Optional[str] = None,
                 api_key: Optional[str] = None,
                 api_base: Optional[str] = None,
                 model: Optional[str] = None,
                 use_cache: bool = True,
                 china_config: Optional[Dict[str, Any]] = None):
        """
        初始化智能翻译器
        
        Args:
            ai_provider: "openai", "claude", "ollama" 或 None
            api_key: API 密钥
            api_base: API 基础地址
            model: 模型名称
            use_cache: 是否使用缓存
            china_config: 国内翻译API配置，如 {"baidu": {"app_id": "xxx", "app_key": "xxx"}}
        """
        self.ai_translator = None
        self.china_translator = None
        self.fallback_translator = SimpleTranslator()
        self.cache = TranslationCache() if use_cache else None
        
        # 初始化 AI 翻译器
        if ai_provider:
            self.ai_translator = AITranslator(
                provider=ai_provider,
                api_key=api_key,
                api_base=api_base,
                model=model
            )
            if not self.ai_translator.is_available():
                logger.warning(f"AI translator ({ai_provider}) not available")
                self.ai_translator = None
        
        # 初始化国内翻译API
        if china_config:
            try:
                from src.core.translator_china import ChinaTranslatorManager
                self.china_translator = ChinaTranslatorManager(china_config)
            except ImportError:
                logger.debug("⚠️ translator_china module not available")
    
    def is_available(self) -> bool:
        """检查是否有可用的翻译方式"""
        return (self.ai_translator and self.ai_translator.is_available()) or \
               (self.china_translator and self.china_translator.is_available()) or \
               self.fallback_translator.is_available()
    
    def _is_japanese(self, text: str) -> bool:
        """检测文本是否主要是日文"""
        hiragana = len(re.findall(r'[\u3040-\u309F]', text))
        katakana = len(re.findall(r'[\u30A0-\u30FF]', text))
        return (hiragana + katakana) > len(text) * 0.1
    
    def _is_chinese(self, text: str) -> bool:
        """检测文本是否主要是中文"""
        chinese_chars = len(re.findall(r'[\u4E00-\u9FFF]', text))
        return chinese_chars > len(text) * 0.3
    
    async def translate(self, text: str, target_lang: str = "ja") -> str:
        """
        智能翻译
        
        优先级：
        1. 检查缓存
        2. 尝试 AI 翻译（质量最高）
        3. 国内翻译 API（百度/有道/小牛，国内访问快）
        4. Google 翻译（免费备选）
        """
        if not text or not text.strip():
            return text
        
        # 检测是否需要翻译
        if target_lang == "ja" and self._is_japanese(text):
            return text
        if target_lang == "zh" and self._is_chinese(text):
            return text
        
        # 检查缓存
        if self.cache:
            cached = self.cache.get(text, target_lang)
            if cached:
                logger.debug(f"Cache hit: '{text[:40]}...'")
                return cached
        
        translated = None
        
        # 1. 尝试 AI 翻译
        if self.ai_translator and self.ai_translator.is_available():
            try:
                translated = await self.ai_translator.translate(text, target_lang)
            except Exception as e:
                logger.warning(f"AI translation failed: {e}")
        
        # 2. 尝试国内翻译 API
        if (translated is None or translated == text) and \
           self.china_translator and self.china_translator.is_available():
            try:
                translated = await self.china_translator.translate(text, target_lang)
            except Exception as e:
                logger.warning(f"China API translation failed: {e}")
        
        # 3. 回退到 Google 翻译
        if translated is None or translated == text:
            translated = await self.fallback_translator.translate(text, target_lang)
        
        # 保存到缓存
        if self.cache and translated and translated != text:
            self.cache.set(text, target_lang, translated)
        
        return translated or text


# 便捷的预设配置
def create_translator(config: Optional[Dict[str, Any]] = None) -> SmartTranslator:
    """
    根据配置创建翻译器
    
    配置示例:
    {
        "provider": "openai",  # "openai", "claude", "ollama"
        "api_key": "sk-...",
        "api_base": None,  # 可选，用于代理或本地模型
        "model": "gpt-4o-mini",  # 可选
        "use_cache": True,
        "china": {  # 国内翻译API配置（可选）
            "baidu": {"app_id": "xxx", "app_key": "xxx"},
            "youdao": {"app_id": "xxx", "app_key": "xxx"},
            "niutrans": {"api_key": "xxx"}
        }
    }
    """
    if config is None:
        # 尝试从环境变量读取
        import os
        
        # 构建国内API配置
        china_config = {}
        
        # 百度翻译
        if os.environ.get("BAIDU_APP_ID") and os.environ.get("BAIDU_APP_KEY"):
            china_config["baidu"] = {
                "app_id": os.environ.get("BAIDU_APP_ID"),
                "app_key": os.environ.get("BAIDU_APP_KEY")
            }
        
        # 有道翻译
        if os.environ.get("YOUDAO_APP_ID") and os.environ.get("YOUDAO_APP_KEY"):
            china_config["youdao"] = {
                "app_id": os.environ.get("YOUDAO_APP_ID"),
                "app_key": os.environ.get("YOUDAO_APP_KEY")
            }
        
        # 小牛翻译
        if os.environ.get("NIUTRANS_API_KEY"):
            china_config["niutrans"] = {
                "api_key": os.environ.get("NIUTRANS_API_KEY")
            }
        
        # 优先检查 OpenAI
        if os.environ.get("OPENAI_API_KEY"):
            return SmartTranslator(
                ai_provider="openai",
                api_key=os.environ.get("OPENAI_API_KEY"),
                api_base=os.environ.get("OPENAI_API_BASE"),
                model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
                use_cache=True,
                china_config=china_config if china_config else None
            )
        
        # 检查 Claude
        if os.environ.get("ANTHROPIC_API_KEY"):
            return SmartTranslator(
                ai_provider="claude",
                api_key=os.environ.get("ANTHROPIC_API_KEY"),
                model=os.environ.get("CLAUDE_MODEL", "claude-3-haiku-20240307"),
                use_cache=True,
                china_config=china_config if china_config else None
            )
        
        # 检查 Ollama
        if os.environ.get("OLLAMA_ENABLED", "false").lower() == "true":
            return SmartTranslator(
                ai_provider="ollama",
                api_base=os.environ.get("OLLAMA_HOST", "http://localhost:11434"),
                model=os.environ.get("OLLAMA_MODEL", "qwen2.5:7b"),
                use_cache=True,
                china_config=china_config if china_config else None
            )
        
        # 如果配置了国内API但没有AI翻译，使用国内API
        if china_config:
            return SmartTranslator(
                ai_provider=None,
                use_cache=True,
                china_config=china_config
            )
        
        # 默认只用 Google
        return SmartTranslator(ai_provider=None)
    
    return SmartTranslator(
        ai_provider=config.get("provider"),
        api_key=config.get("api_key"),
        api_base=config.get("api_base"),
        model=config.get("model"),
        use_cache=config.get("use_cache", True),
        china_config=config.get("china")
    )


# 单例实例
_translator: Optional[SmartTranslator] = None


def get_translator(config: Optional[Dict[str, Any]] = None) -> SmartTranslator:
    """获取翻译器单例"""
    global _translator
    if _translator is None:
        _translator = create_translator(config)
    return _translator
