#!/usr/bin/env python3
"""
GPT-SoVITS TTS Provider (API v2) - 合并 Windows 版改进
支持本地和远程（SSH 隧道）GPT-SoVITS 服务
"""

import os
import sys
import time
import asyncio
import tempfile
from typing import Optional, Dict, Any
from pathlib import Path
from dataclasses import dataclass

from loguru import logger

# 🚨 避免循环导入：直接定义基类，不依赖 tts_manager
from dataclasses import dataclass as dc
from typing import Optional

@dc
class TTSResult:
    """TTS 结果数据类"""
    audio_path: str
    text: str
    duration_ms: float
    sample_rate: int
    success: bool
    error: Optional[str] = None


class BaseTTSProvider:
    """TTS 提供者基类"""
    def __init__(self, name: str):
        self.name = name
        self._initialized = False
    
    def is_available(self) -> bool:
        return self._initialized
    
    async def speak(self, text: str, voice_id: Optional[str] = None) -> TTSResult:
        raise NotImplementedError


@dataclass
class GPTSoVITSConfig:
    """GPT-SoVITS 配置 (适配 api_v2.py)"""
    api_url: str = "http://127.0.0.1:9880/tts"  # 默认端口
    text_language: str = "zh"  # 文本语言: zh, en, ja, auto, yue
    refer_wav_path: Optional[str] = None  # 参考音频路径
    prompt_text: Optional[str] = None  # 参考音频文本
    prompt_language: str = "zh"  # 参考音频语言
    # api_v2 特有参数
    text_split_method: str = "cut5"  # 文本分割方法: cut0-5
    batch_size: int = 1  # 批次大小
    media_type: str = "wav"  # 音频格式: wav, mp3, ogg
    streaming_mode: bool = False  # 是否流式输出
    # 采样参数
    top_k: int = 20
    top_p: float = 0.6
    temperature: float = 0.6
    speed: float = 1.0  # 语速
    # SSH 隧道配置
    ssh_host: Optional[str] = None  # SSH Config 别名或 IP
    ssh_user: Optional[str] = None  # SSH 用户名（可选）
    ssh_key: Optional[str] = None  # SSH 私钥路径（可选）


class GPTSoVITSProvider(BaseTTSProvider):
    """
    GPT-SoVITS TTS Provider (API v2)
    支持通过 API 调用 GPT-SoVITS api_v2.py 生成高质量语音
    
    特性:
    - 支持本地和远程（SSH 隧道）服务
    - 使用 GET 请求 + 查询参数（api_v2 标准）
    - 自动检测语言
    - 支持语速调节 (speed)
    """
    
    # 语言代码映射
    LANG_MAP = {
        "zh": "zh",
        "zh-cn": "zh",
        "jp": "ja",
        "ja": "ja",
        "en": "en",
        "yue": "yue",  # 粤语
        "auto": "auto",
    }
    
    def __init__(self, config: Optional[GPTSoVITSConfig] = None):
        super().__init__("GPT-SoVITS")
        
        # 从环境变量构建配置
        self.config = config or self._config_from_env()
        
        # SSH 隧道
        self._ssh_tunnel = None
        self._setup_ssh_tunnel()
        
        # 检查可用性
        self._initialized = False
        self._check_availability()
    
    def _config_from_env(self) -> GPTSoVITSConfig:
        """从环境变量读取配置"""
        # 🚨 调试：打印环境变量
        refer_wav = os.environ.get("GPT_SOVITS_REFER_WAV", "")
        prompt_text = os.environ.get("GPT_SOVITS_PROMPT_TEXT", "")
        
        logger.info(f"🎙️ GPT-SoVITS 环境变量:")
        logger.info(f"   GPT_SOVITS_URL={os.environ.get('GPT_SOVITS_URL', '默认')}")
        logger.info(f"   GPT_SOVITS_REFER_WAV={refer_wav if refer_wav else '未设置'}")
        logger.info(f"   GPT_SOVITS_PROMPT_TEXT={prompt_text[:30] if prompt_text else '未设置'}...")
        
        return GPTSoVITSConfig(
            api_url=os.environ.get("GPT_SOVITS_URL", "http://127.0.0.1:9880/tts"),
            text_language=os.environ.get("GPT_SOVITS_LANG", "zh"),
            refer_wav_path=refer_wav or None,
            prompt_text=prompt_text or None,
            prompt_language=os.environ.get("GPT_SOVITS_PROMPT_LANG", "zh"),
            text_split_method=os.environ.get("GPT_SOVITS_SPLIT_METHOD", "cut5"),
            batch_size=int(os.environ.get("GPT_SOVITS_BATCH_SIZE", "1")),
            media_type=os.environ.get("GPT_SOVITS_MEDIA_TYPE", "wav"),
            streaming_mode=os.environ.get("GPT_SOVITS_STREAMING", "").lower() == "true",
            top_k=int(os.environ.get("GPT_SOVITS_TOP_K", "20")),
            top_p=float(os.environ.get("GPT_SOVITS_TOP_P", "0.6")),
            temperature=float(os.environ.get("GPT_SOVITS_TEMPERATURE", "0.6")),
            speed=float(os.environ.get("GPT_SOVITS_SPEED", "1.0")),
            ssh_host=os.environ.get("SSH_TUNNEL_HOST") or None,
            ssh_user=os.environ.get("SSH_TUNNEL_USER") or None,
            ssh_key=os.environ.get("SSH_TUNNEL_KEY") or None,
        )
    
    def _setup_ssh_tunnel(self):
        """设置 SSH 隧道（如果需要）"""
        if not self.config.ssh_host:
            return
        
        try:
            from src.core.ssh_tunnel import SSHTunnelManager, SSHTunnelConfig
            
            tunnel_config = SSHTunnelConfig(
                remote_host=self.config.ssh_host,
                ssh_user=self.config.ssh_user or "",
                ssh_key=self.config.ssh_key or "",
                remote_port=9880,
                local_port=9880,
            )
            
            self._ssh_tunnel = SSHTunnelManager(tunnel_config)
            if self._ssh_tunnel.start():
                logger.info("🔌 GPT-SoVITS: SSH 隧道已建立")
                time.sleep(2)  # 等待隧道稳定
            else:
                logger.warning("⚠️ SSH 隧道建立失败")
                self._ssh_tunnel = None
        except Exception as e:
            logger.warning(f"⚠️ SSH 隧道设置失败: {e}")
            self._ssh_tunnel = None
    
    def _map_language(self, lang: str) -> str:
        """映射语言代码"""
        return self.LANG_MAP.get(lang.lower(), lang)
    
    def _get_language(self, text: str) -> str:
        """
        获取文本语言代码
        直接使用菜单栏选择的语言配置
        """
        config_lang = self.config.text_language.lower()
        
        # 中文
        if config_lang in ("zh", "zh-cn", "zh_cn", "chinese"):
            return "zh"
        
        # 日语
        if config_lang in ("jp", "ja", "japanese"):
            return "ja"
        
        # 英语
        if config_lang in ("en", "english"):
            return "en"
        
        # 粤语
        if config_lang in ("yue", "cantonese"):
            return "yue"
        
        # 默认：中文
        return "zh"
    
    def _check_availability(self):
        """检查 GPT-SoVITS 服务是否可用"""
        try:
            import aiohttp
            self._initialized = True
            logger.info(f"✅ GPT-SoVITS provider initialized (API: {self.config.api_url})")
        except ImportError:
            self._initialized = False
            logger.warning("⚠️ aiohttp not found. Install with: pip install aiohttp")
    
    def is_available(self) -> bool:
        return self._initialized
    
    def update_config(self, **kwargs):
        """更新配置"""
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
                logger.info(f"📝 GPT-SoVITS config updated: {key} = {value}")
    
    async def speak(self, text: str, voice_id: Optional[str] = None) -> TTSResult:
        """
        使用 GPT-SoVITS api_v2 生成语音
        
        Args:
            text: 要合成的文本
            voice_id: 可选，参考音频路径
        
        Returns:
            TTSResult: 包含音频文件路径的结果
        """
        if not self._initialized:
            return TTSResult(
                audio_path="",
                text=text,
                duration_ms=0,
                sample_rate=32000,
                success=False,
                error="GPT-SoVITS not initialized"
            )
        
        # 创建临时文件
        with tempfile.NamedTemporaryFile(suffix=f".{self.config.media_type}", delete=False) as f:
            output_path = f.name
        
        try:
            import aiohttp
            
            # 获取语言（根据菜单栏选择）
            text_language = self._get_language(text)
            
            # 确定参考音频路径
            # 🚨 注意：路径可能在远程服务器上，不需要本地存在
            ref_audio_path = None
            if voice_id:
                ref_audio_path = voice_id
            elif self.config.refer_wav_path:
                ref_audio_path = self.config.refer_wav_path
            
            if not ref_audio_path:
                logger.error("❌ GPT-SoVITS: 需要提供参考音频 (refer_wav_path)")
                return TTSResult(
                    audio_path="",
                    text=text,
                    duration_ms=0,
                    sample_rate=32000,
                    success=False,
                    error="GPT-SoVITS api_v2 requires reference audio"
                )
            
            # 🚨 调试：打印实际使用的路径
            logger.debug(f"🎙️ GPT-SoVITS: 使用参考音频: {ref_audio_path}")
            
            # 🚨 Windows 版改进: 使用 GET 请求 + 查询参数
            params = {
                "text": text,
                "text_lang": text_language,
                "ref_audio_path": ref_audio_path,
                "prompt_lang": self._map_language(self.config.prompt_language),
                "text_split_method": self.config.text_split_method,
                "batch_size": self.config.batch_size,
                "media_type": self.config.media_type,
                "streaming_mode": str(self.config.streaming_mode).lower(),
                "top_k": self.config.top_k,
                "top_p": self.config.top_p,
                "temperature": self.config.temperature,
                "speed": self.config.speed,
            }
            
            # 添加 prompt_text（如果配置了）
            if self.config.prompt_text:
                params["prompt_text"] = self.config.prompt_text
            
            logger.info(f"🎙️ GPT-SoVITS: '{text[:30]}...' (语言: {text_language}, 语速: {self.config.speed}x)")
            
            # 🚨 Windows 版改进: GET 请求 api_v2
            timeout = aiohttp.ClientTimeout(total=120)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(
                    self.config.api_url,
                    params=params
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(f"API error {response.status}: {error_text[:500]}")
                    
                    # 保存音频
                    audio_data = await response.read()
                    if len(audio_data) < 100:
                        raise Exception("Invalid audio data received")
                    
                    with open(output_path, "wb") as f:
                        f.write(audio_data)
            
            # 🚨 Windows 版改进: 使用 wave 库精确计算音频时长
            duration_ms = await self._get_audio_duration(output_path, text)
            
            logger.info(f"✅ GPT-SoVITS: 生成完成 ({duration_ms/1000:.1f}s, {len(audio_data)} bytes)")
            
            return TTSResult(
                audio_path=output_path,
                text=text,
                duration_ms=duration_ms,
                sample_rate=32000,
                success=True
            )
            
        except asyncio.TimeoutError:
            logger.error("❌ GPT-SoVITS: 请求超时")
            self._cleanup_file(output_path)
            return TTSResult(
                audio_path="",
                text=text,
                duration_ms=0,
                sample_rate=32000,
                success=False,
                error="Request timeout"
            )
        except Exception as e:
            logger.error(f"❌ GPT-SoVITS error: {e}")
            self._cleanup_file(output_path)
            return TTSResult(
                audio_path="",
                text=text,
                duration_ms=0,
                sample_rate=32000,
                success=False,
                error=str(e)
            )
    
    async def _get_audio_duration(self, audio_path: str, text: str = "") -> float:
        """🚨 Windows 版改进: 使用 wave 库精确计算音频时长"""
        try:
            import wave
            with wave.open(audio_path, 'rb') as wav:
                frames = wav.getnframes()
                rate = wav.getframerate()
                if rate > 0:
                    return (frames / rate) * 1000
        except Exception as e:
            logger.debug(f"Wave duration check failed: {e}")
        
        # 回退：根据文件大小估算
        try:
            file_size = os.path.getsize(audio_path)
            # WAV: 32000Hz, 16bit, 单声道 = 64000 bytes/second
            if audio_path.endswith('.wav'):
                return max(1000, (file_size - 44) / 64000 * 1000)
        except:
            pass
        
        # 最终回退：根据文本长度
        return len(text) * 220
    
    def _cleanup_file(self, filepath: str):
        """清理临时文件"""
        try:
            if os.path.exists(filepath):
                os.unlink(filepath)
        except:
            pass
    
    async def check_health(self) -> bool:
        """检查 GPT-SoVITS 服务健康状态"""
        try:
            import aiohttp
            base_url = self.config.api_url.rsplit('/', 1)[0]
            async with aiohttp.ClientSession() as session:
                async with session.get(base_url, timeout=5) as response:
                    return response.status < 500
        except:
            return False
    
    def stop(self):
        """停止 SSH 隧道"""
        if self._ssh_tunnel:
            self._ssh_tunnel.stop()
            logger.info("🔌 GPT-SoVITS: SSH 隧道已关闭")


class GPTSoVITSProviderSimple(GPTSoVITSProvider):
    """
    简化版 GPT-SoVITS Provider
    快速初始化，使用环境变量或默认值
    """
    
    def __init__(self, api_url: str = "http://127.0.0.1:9880", 
                 refer_wav_path: Optional[str] = None,
                 prompt_text: Optional[str] = None):
        config = GPTSoVITSConfig(
            api_url=api_url if api_url.endswith('/tts') else f"{api_url}/tts",
            refer_wav_path=refer_wav_path,
            prompt_text=prompt_text
        )
        super().__init__(config)
        self.name = "GPT-SoVITS-Simple"


# 兼容性别名
GPTSoVITSTTSProvider = GPTSoVITSProvider


class GPTSoVITSProxyProvider(BaseTTSProvider):
    """
    GPT-SoVITS Proxy Provider - 多音色版本
    使用 Mac 本地代理 http://127.0.0.1:8000，通过 voice 参数直接选择音色

    API: POST http://127.0.0.1:8000/v1/audio/speech
    Body: {"input": "text", "voice": "voicename"}
    """

    def __init__(self, api_url: str = "http://127.0.0.1:8000"):
        super().__init__("GPT-SoVITS-Proxy")
        self.api_url = api_url.rstrip('/') + "/v1/audio/speech"
        self._voice_id: str = "sakiko1"  # 默认音色
        self._speed: float = 1.0
        self._initialized = True
        # 🚀 音频缓存：{cache_key: audio_path}
        self._cache: dict[str, str] = {}
        self._cache_dir = os.path.join(tempfile.gettempdir(), "sherry_tts_cache")
        os.makedirs(self._cache_dir, exist_ok=True)
        logger.info(f"✅ GPT-SoVITS-Proxy initialized: {self.api_url}, cache dir: {self._cache_dir}")

    @property
    def voice_id(self) -> str:
        return self._voice_id

    @voice_id.setter
    def voice_id(self, value: str):
        self._voice_id = value
        logger.info(f"🎙️ GPT-SoVITS-Proxy 音色切换: {value}")

    def set_speed(self, speed: float):
        self._speed = speed

    def is_available(self) -> bool:
        return self._initialized

    def _get_cache_key(self, text: str, voice: str) -> str:
        """生成缓存 key（基于 text 和 voice 的 hash）"""
        import hashlib
        key = f"{voice}:{text}"
        return hashlib.md5(key.encode()).hexdigest()

    async def speak(self, text: str, voice_id: Optional[str] = None) -> TTSResult:
        """使用代理 API 生成语音（带缓存）"""
        voice = voice_id or self._voice_id

        # 🚀 检查缓存
        cache_key = self._get_cache_key(text, voice)
        cached_path = os.path.join(self._cache_dir, f"{cache_key}.wav")
        if os.path.exists(cached_path):
            duration_ms = await self._get_audio_duration(cached_path, text)
            logger.info(f"🎙️ GPT-SoVITS-Proxy 缓存命中: {text[:20]}... (voice: {voice})")
            return TTSResult(
                audio_path=cached_path,
                text=text,
                duration_ms=duration_ms,
                sample_rate=24000,
                success=True
            )

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            output_path = f.name

        # 代理返回 ogg 格式，下载后转码为 wav
        ogg_path = output_path + ".ogg"

        try:
            import aiohttp

            payload = {
                "input": text,
                "voice": voice
            }

            logger.info(f"🎙️ GPT-SoVITS-Proxy: '{text[:30]}...' (voice: {voice}, speed: {self._speed})")

            timeout = aiohttp.ClientTimeout(total=120)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(
                    self.api_url,
                    json=payload,
                    headers={"Content-Type": "application/json"}
                ) as response:
                    if response.status == 400:
                        error_text = await response.text()
                        raise Exception(f"Voice not found or invalid: {error_text[:200]}")
                    elif response.status != 200:
                        error_text = await response.text()
                        raise Exception(f"API error {response.status}: {error_text[:500]}")

                    audio_data = await response.read()
                    if len(audio_data) < 100:
                        raise Exception("Invalid audio data received")

                    with open(ogg_path, "wb") as f:
                        f.write(audio_data)

                    # 转码为 WAV（afplay 对 opus/ogg 支持不完整）
                    import subprocess
                    result = subprocess.run(
                        ["ffmpeg", "-y", "-i", ogg_path, "-acodec", "pcm_s16le", "-ar", "24000", cached_path],
                        capture_output=True, timeout=30
                    )
                    if result.returncode != 0:
                        raise Exception(f"WAV conversion failed: {result.stderr.decode()[:200]}")
                    # 删除临时 ogg 和原始 temp wav 文件
                    os.unlink(ogg_path)
                    if os.path.exists(output_path):
                        os.unlink(output_path)
                    # 更新缓存记录
                    self._cache[cache_key] = cached_path

            duration_ms = await self._get_audio_duration(cached_path, text)
            logger.info(f"✅ GPT-SoVITS-Proxy: 生成完成 ({duration_ms/1000:.1f}s)")

            return TTSResult(
                audio_path=cached_path,
                text=text,
                duration_ms=duration_ms,
                sample_rate=24000,
                success=True
            )

        except asyncio.TimeoutError:
            logger.error("❌ GPT-SoVITS-Proxy: 请求超时")
            self._cleanup_file(output_path)
            self._cleanup_file(ogg_path)
            return TTSResult(audio_path="", text=text, duration_ms=0, sample_rate=32000, success=False, error="Timeout")
        except Exception as e:
            logger.error(f"❌ GPT-SoVITS-Proxy error: {e}")
            self._cleanup_file(output_path)
            self._cleanup_file(ogg_path)
            return TTSResult(audio_path="", text=text, duration_ms=0, sample_rate=32000, success=False, error=str(e))

    async def _get_audio_duration(self, audio_path: str, text: str = "") -> float:
        """计算音频时长"""
        try:
            import wave
            with wave.open(audio_path, 'rb') as wav:
                frames = wav.getnframes()
                rate = wav.getframerate()
                if rate > 0:
                    return (frames / rate) * 1000
        except Exception:
            pass
        return len(text) * 220

    def _cleanup_file(self, filepath: str):
        try:
            if os.path.exists(filepath):
                os.unlink(filepath)
        except Exception:
            pass

    async def check_health(self) -> bool:
        """检查代理服务健康状态"""
        try:
            import aiohttp
            health_url = self.api_url.rsplit('/v1/audio/speech', 1)[0] + "/health"
            async with aiohttp.ClientSession() as session:
                async with session.get(health_url, timeout=aiohttp.ClientTimeout(total=5)) as response:
                    return response.status == 200
        except Exception:
            return False
