#!/usr/bin/env python3
"""
TTS Manager - Text-to-Speech management with multiple providers
Supports: Edge TTS (default), ElevenLabs, Local TTS
Handles audio playback and lip sync integration
"""

import os
import sys
import hashlib

# Import asyncio first to avoid subprocess.Popen type issues on Windows
import asyncio
import tempfile
import subprocess
import wave
import struct
import random

# Windows: 全局设置 subprocess 不显示终端窗口
if sys.platform == 'win32':
    # 创建一个启动信息对象，隐藏终端窗口
    _startupinfo = subprocess.STARTUPINFO()
    _startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    _startupinfo.wShowWindow = subprocess.SW_HIDE
    
    # 保存原始的 Popen
    _original_popen = subprocess.Popen
    
    # 创建包装函数，自动添加隐藏窗口标志
    def _hidden_popen(*args, **kwargs):
        if 'startupinfo' not in kwargs:
            kwargs['startupinfo'] = _startupinfo
        if 'creationflags' not in kwargs:
            kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW
        return _original_popen(*args, **kwargs)
    
    # 替换 Popen
    subprocess.Popen = _hidden_popen
    
    # 同时修改 run 和 call 的默认行为
    _original_run = subprocess.run
    def _hidden_run(*args, **kwargs):
        if 'startupinfo' not in kwargs:
            kwargs['startupinfo'] = _startupinfo
        if 'creationflags' not in kwargs:
            kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW
        return _original_run(*args, **kwargs)
    subprocess.run = _hidden_run

# Configure FFmpeg path for pydub on Windows
if sys.platform == 'win32':
    ffmpeg_bin = r"C:\ffmpeg\ffmpeg-8.0.1-full_build-shared\bin"
    if os.path.exists(ffmpeg_bin):
        os.environ["PATH"] = ffmpeg_bin + os.pathsep + os.environ.get("PATH", "")
        os.environ["FFMPEG_BINARY"] = os.path.join(ffmpeg_bin, "ffmpeg.exe")
        os.environ["FFPROBE_BINARY"] = os.path.join(ffmpeg_bin, "ffprobe.exe")

import numpy as np
from pathlib import Path
from typing import Optional, Callable, List, Dict, Any
from concurrent.futures import ThreadPoolExecutor

# Import base classes from separate module to avoid circular imports
from src.core.tts_provider_base import BaseTTSProvider, TTSResult

from PyQt6.QtCore import QObject, pyqtSignal, QThread, QTimer
from loguru import logger

# Import GPT-SoVITS providers (optional)
try:
    from src.core.gpt_sovits_provider import (
        GPTSoVITSProvider, GPTSoVITSConfig, GPTSoVITSProxyProvider
    )
    GPT_SOVITS_AVAILABLE = True
except ImportError:
    GPT_SOVITS_AVAILABLE = False

# Import translator (optional)
try:
    from src.core.translator import SmartTranslator, create_translator
    TRANSLATOR_AVAILABLE = True
except ImportError:
    TRANSLATOR_AVAILABLE = False


def is_apple_silicon() -> bool:
    """Check if running on Apple Silicon"""
    import platform
    return platform.machine() == 'arm64' and platform.system() == 'Darwin'


class EdgeTTSProvider(BaseTTSProvider):
    """
    Edge TTS Provider - Using Microsoft's Edge TTS service
    Voice: zh-CN-XiaoxiaoNeural (default Chinese female voice)
    """
    
    DEFAULT_VOICE = "zh-CN-XiaoxiaoNeural"
    
    def __init__(self, voice: Optional[str] = None, rate: str = "+0%", pitch: str = "+0Hz"):
        super().__init__("EdgeTTS")
        self.voice = voice or self.DEFAULT_VOICE
        self.rate = rate
        self.pitch = pitch
        self._check_edge_tts()
    
    def _check_edge_tts(self):
        """Check if edge-tts is installed"""
        try:
            import edge_tts
            self._initialized = True
            logger.info("✅ EdgeTTS provider initialized")
        except ImportError:
            self._initialized = False
            logger.warning("⚠️ edge-tts not found. Install with: pip install edge-tts")
    
    def is_available(self) -> bool:
        return self._initialized
    
    async def speak(self, text: str, voice_id: Optional[str] = None) -> TTSResult:
        """Generate audio using edge-tts"""
        if not self._initialized:
            return TTSResult(
                audio_path="",
                text=text,
                duration_ms=0,
                sample_rate=24000,
                success=False,
                error="EdgeTTS not initialized"
            )
        
        voice = voice_id or self.voice
        
        # Create temp file for audio output
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            output_path = f.name
        
        try:
            # Use edge_tts Python library directly
            import edge_tts
            communicate = edge_tts.Communicate(text, voice=voice, rate=self.rate, pitch=self.pitch)
            await communicate.save(output_path)
            
            # Get audio duration
            duration_ms = await self._get_audio_duration(output_path, text)
            
            return TTSResult(
                audio_path=output_path,
                text=text,
                duration_ms=duration_ms,
                sample_rate=24000,
                success=True
            )
            
        except Exception as e:
            logger.error(f"❌ EdgeTTS error: {e}")
            # Clean up temp file
            try:
                os.unlink(output_path)
            except:
                pass
            return TTSResult(
                audio_path="",
                text=text,
                duration_ms=0,
                sample_rate=24000,
                success=False,
                error=str(e)
            )
    
    async def _get_audio_duration(self, audio_path: str, text: str = "") -> float:
        """Get audio duration in milliseconds"""
        try:
            # Windows: hide terminal window (全局 hook 已设置，但显式传递更安全)
            kwargs = {}
            if sys.platform == 'win32':
                kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW
            result = subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries", 
                 "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", audio_path],
                capture_output=True, text=True, **kwargs
            )
            duration_sec = float(result.stdout.strip())
            return duration_sec * 1000
        except:
            # Fallback: estimate based on text length
            return len(text) * 200 if text else 3000  # ~200ms per character


class ElevenLabsProvider(BaseTTSProvider):
    """
    ElevenLabs TTS Provider (Premium quality)
    Requires API key in environment: ELEVENLABS_API_KEY
    """
    
    DEFAULT_VOICE = "21m00Tcm4TlvDq8ikWAM"  # Rachel
    API_BASE = "https://api.elevenlabs.io/v1"
    
    def __init__(self, api_key: Optional[str] = None, voice_id: Optional[str] = None):
        super().__init__("ElevenLabs")
        self.api_key = api_key or os.environ.get("ELEVENLABS_API_KEY", "")
        self.voice_id = voice_id or self.DEFAULT_VOICE
        self._initialized = bool(self.api_key)
        if self._initialized:
            logger.info("✅ ElevenLabs provider initialized")
    
    def is_available(self) -> bool:
        return self._initialized
    
    async def speak(self, text: str, voice_id: Optional[str] = None) -> TTSResult:
        """Generate audio using ElevenLabs API"""
        if not self._initialized:
            return TTSResult(
                audio_path="",
                text=text,
                duration_ms=0,
                sample_rate=44100,
                success=False,
                error="ElevenLabs API key not set"
            )
        
        voice = voice_id or self.voice_id
        
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            output_path = f.name
        
        try:
            import aiohttp
            
            url = f"{self.API_BASE}/text-to-speech/{voice}"
            headers = {
                "xi-api-key": self.api_key,
                "Content-Type": "application/json"
            }
            data = {
                "text": text,
                "model_id": "eleven_multilingual_v2",
                "voice_settings": {
                    "stability": 0.5,
                    "similarity_boost": 0.5
                }
            }
            
            logger.info(f"🎙️ ElevenLabs: generating audio for '{text[:30]}...'")
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=data) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(f"ElevenLabs API error: {error_text}")
                    
                    audio_data = await response.read()
                    with open(output_path, "wb") as f:
                        f.write(audio_data)
            
            # Estimate duration
            duration_ms = len(text) * 180  # ~180ms per character
            
            return TTSResult(
                audio_path=output_path,
                text=text,
                duration_ms=duration_ms,
                sample_rate=44100,
                success=True
            )
            
        except Exception as e:
            logger.error(f"❌ ElevenLabs error: {e}")
            try:
                os.unlink(output_path)
            except:
                pass
            return TTSResult(
                audio_path="",
                text=text,
                duration_ms=0,
                sample_rate=44100,
                success=False,
                error=str(e)
            )


class LocalTTSProvider(BaseTTSProvider):
    """
    Local TTS Provider using system TTS
    macOS: say command
    Linux: espeak or festival
    Windows: sapi5 via pyttsx3
    """
    
    def __init__(self):
        super().__init__("LocalTTS")
        self.platform = os.uname().sysname if hasattr(os, 'uname') else 'Unknown'
        self._initialized = self._check_availability()
    
    def _check_availability(self) -> bool:
        """Check local TTS availability"""
        import platform as pf
        
        if pf.system() == 'Darwin':  # macOS
            try:
                subprocess.run(["say", "-v", "?"], capture_output=True, check=True)
                logger.info("✅ LocalTTS provider initialized (macOS say)")
                return True
            except:
                return False
        elif pf.system() == 'Linux':
            try:
                subprocess.run(["which", "espeak"], capture_output=True, check=True)
                logger.info("✅ LocalTTS provider initialized (Linux espeak)")
                return True
            except:
                return False
        else:
            try:
                import pyttsx3
                logger.info("✅ LocalTTS provider initialized (Windows pyttsx3)")
                return True
            except ImportError:
                return False
    
    def is_available(self) -> bool:
        return self._initialized
    
    async def speak(self, text: str, voice_id: Optional[str] = None) -> TTSResult:
        """Generate audio using local TTS"""
        import platform as pf
        
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            output_path = f.name
        
        try:
            if pf.system() == 'Darwin':  # macOS
                # Use say command with output to file
                voice = voice_id or "Ting-Ting"  # Chinese voice
                cmd = ["say", "-v", voice, "-o", output_path, text]
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                await process.communicate()
                
            elif pf.system() == 'Linux':
                cmd = ["espeak", "-w", output_path, "-v", "zh", text]
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                await process.communicate()
                
            else:  # Windows
                # Use pyttsx3 for Windows TTS
                import pyttsx3
                engine = pyttsx3.init()
                engine.say(text)
                engine.runAndWait()
                # Return result without file since pyttsx3 plays directly
                return TTSResult(
                    audio_path="",
                    text=text,
                    duration_ms=len(text) * 200,
                    sample_rate=22050,
                    success=True
                )
            
            duration_ms = len(text) * 200
            
            return TTSResult(
                audio_path=output_path,
                text=text,
                duration_ms=duration_ms,
                sample_rate=22050,
                success=True
            )
            
        except Exception as e:
            logger.error(f"❌ LocalTTS error: {e}")
            try:
                os.unlink(output_path)
            except:
                pass
            return TTSResult(
                audio_path="",
                text=text,
                duration_ms=0,
                sample_rate=22050,
                success=False,
                error=str(e)
            )


class AudioAnalyzer:
    """
    Audio amplitude analyzer for lip sync
    Extracts volume/amplitude data from audio files
    """
    
    def __init__(self, frame_rate: int = 30):
        self.frame_rate = frame_rate
        self._executor = ThreadPoolExecutor(max_workers=2)
    
    def analyze_amplitude(self, audio_path: str, duration_ms: float = 3000) -> List[float]:
        """
        Analyze audio file and return amplitude values per frame
        Returns list of normalized amplitude values (0.0 - 1.0)
        """
        try:
            # Try fast path: use pydub directly (no WAV conversion needed)
            from pydub import AudioSegment
            
            audio = AudioSegment.from_file(audio_path)
            audio = audio.set_frame_rate(24000).set_channels(1)
            
            # Get raw samples
            samples = np.array(audio.get_array_of_samples())
            frame_rate = audio.frame_rate
            
            # Calculate samples per frame (30fps)
            samples_per_frame = frame_rate // self.frame_rate
            n_analysis_frames = len(samples) // samples_per_frame
            
            # Calculate amplitude for each frame
            amplitudes = []
            for i in range(n_analysis_frames):
                start = i * samples_per_frame
                end = start + samples_per_frame
                frame_samples = samples[start:end]
                
                # RMS amplitude
                rms = np.sqrt(np.mean(frame_samples.astype(np.float64) ** 2))
                # Normalize (16-bit audio max value is 32768)
                normalized = min(rms / 32768.0 * 8, 1.0)
                amplitudes.append(normalized)
            
            logger.info(f"✅ Audio analyzed: {len(amplitudes)} frames")
            return amplitudes
                
        except Exception as e:
            logger.warning(f"Audio analysis failed: {e}, using simulated data")
            return self._generate_simulated_lipsync(duration_ms)
    
    def _generate_simulated_lipsync(self, duration_ms: float) -> List[float]:
        """Generate simulated lip sync data when audio analysis fails"""
        import random
        n_frames = int(duration_ms / 1000 * self.frame_rate)
        amplitudes = []
        for i in range(n_frames):
            # Generate a sine wave pattern with some randomness
            t = i / n_frames
            base = 0.3 + 0.4 * (1 + np.sin(t * 10 * np.pi)) / 2
            noise = random.uniform(0, 0.2)
            amplitudes.append(min(base + noise, 1.0))
        return amplitudes
    
    def _convert_to_wav(self, audio_path: str) -> str:
        """Convert audio file to WAV format if needed"""
        if audio_path.endswith('.wav'):
            return audio_path
        
        # Try using pydub with explicit ffmpeg path
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            wav_path = f.name
        
        try:
            from pydub import AudioSegment
            
            audio = AudioSegment.from_file(audio_path)
            audio = audio.set_frame_rate(24000).set_channels(1)
            audio.export(wav_path, format="wav")
            logger.info("✅ Audio converted successfully with FFmpeg")
            return wav_path
        except Exception as e:
            logger.warning(f"Audio conversion failed: {e}")
            # Return empty to indicate conversion failed
            return ""


class TTSManager(QObject):
    """
    TTS Manager - Central manager for text-to-speech operations
    Handles provider selection, audio playback, and lip sync
    """
    
    # Signals
    tts_started = pyqtSignal(str)  # text
    tts_finished = pyqtSignal()  # no params
    tts_error = pyqtSignal(str)  # error message
    lip_sync_frame = pyqtSignal(float)  # mouth open value (0.0 - 1.0)
    audio_amplitude = pyqtSignal(list)  # list of amplitude values
    
    def __init__(self, parent=None, preferred_provider: str = "edge"):
        super().__init__(parent)
        
        # Load config if available
        config = self._load_config()
        tts_config = config.get("tts", {})
        
        # Initialize providers
        edge_config = tts_config.get("edge", {})
        self.providers: Dict[str, BaseTTSProvider] = {
            "edge": EdgeTTSProvider(
                voice=edge_config.get("voice"),
                rate=edge_config.get("rate", "+0%"),
                pitch=edge_config.get("pitch", "+0Hz")
            ),
            "elevenlabs": ElevenLabsProvider(),
            "local": LocalTTSProvider(),
        }
        
        # Add GPT-SoVITS providers if available
        if GPT_SOVITS_AVAILABLE:
            gptsovits_cfg = tts_config.get("gptsovits", {})
            if gptsovits_cfg.get("enabled", False):
                # Create config from yaml (api_v2 format)
                gs_config = GPTSoVITSConfig(
                    api_url=gptsovits_cfg.get("api_url", "http://127.0.0.1:9880/tts"),
                    text_language=gptsovits_cfg.get("text_lang", "zh"),
                    refer_wav_path=gptsovits_cfg.get("refer_audio_path"),
                    prompt_text=gptsovits_cfg.get("prompt_text"),
                    prompt_language=gptsovits_cfg.get("prompt_lang", "zh"),
                    text_split_method=gptsovits_cfg.get("text_split_method", "cut5"),
                    batch_size=gptsovits_cfg.get("batch_size", 1),
                    media_type=gptsovits_cfg.get("media_type", "wav"),
                    streaming_mode=gptsovits_cfg.get("streaming_mode", False),
                    top_k=gptsovits_cfg.get("top_k", 20),
                    top_p=gptsovits_cfg.get("top_p", 0.6),
                    temperature=gptsovits_cfg.get("temperature", 0.6),
                    speed=gptsovits_cfg.get("speed", 1.0),
                    # SSH 隧道配置
                    ssh_host=os.environ.get("SSH_TUNNEL_HOST") or None,
                    ssh_user=os.environ.get("SSH_TUNNEL_USER") or None,
                    ssh_key=os.environ.get("SSH_TUNNEL_KEY") or None,
                )
                self.providers["gptsovits"] = GPTSoVITSProvider(gs_config)
                logger.info("🎙️ GPT-SoVITS provider loaded with config")
            else:
                self.providers["gptsovits"] = GPTSoVITSProvider()
                logger.info("🎙️ GPT-SoVITS provider loaded (default config)")

            # 多音色代理 Provider
            proxy_cfg = tts_config.get("gptsovits_proxy", {})
            if proxy_cfg.get("enabled", False):
                proxy_url = proxy_cfg.get("api_url", "http://127.0.0.1:8000")
                self.providers["gptsovits_proxy"] = GPTSoVITSProxyProvider(proxy_url)
                default_voice = proxy_cfg.get("default_voice", "sakiko1")
                self.providers["gptsovits_proxy"].voice_id = default_voice
                logger.info(f"🎙️ GPT-SoVITS-Proxy provider loaded (voice: {default_voice})")
            else:
                # 默认也尝试加载代理（不强制要求配置）
                self.providers["gptsovits_proxy"] = GPTSoVITSProxyProvider()
                logger.info("🎙️ GPT-SoVITS-Proxy provider loaded (default)")
        
        # Use config default provider if available
        default_provider = tts_config.get("default_provider", preferred_provider)
        self.current_provider = self._select_provider(default_provider)
        self.audio_analyzer = AudioAnalyzer(frame_rate=30)
        
        # Playback state
        self._is_speaking = False
        self._current_audio_path: Optional[str] = None
        self._amplitude_data: List[float] = []
        self._current_frame = 0
        
        # Playback timer
        self._playback_timer = QTimer(self)
        self._playback_timer.timeout.connect(self._on_playback_frame)
        
        # Cleanup tracking
        self._temp_files: List[str] = []

        # Audio cache for pre-generated dialogue
        self._cache_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "src", "assets", "audio", "tts_cache"
        )
        
        # Translation support with AI translator
        self._auto_translate = tts_config.get("auto_translate", True)
        self._current_language = "zh"  # 当前语言
        
        # Initialize translator with config
        if TRANSLATOR_AVAILABLE:
            translation_cfg = tts_config.get("translation", {})
            
            # 构建配置
            translator_config = {
                "provider": translation_cfg.get("provider"),
                "api_key": translation_cfg.get("api_key"),
                "api_base": translation_cfg.get("api_base"),
                "model": translation_cfg.get("model"),
                "use_cache": translation_cfg.get("use_cache", True),
                "china": translation_cfg.get("china")  # 国内翻译API配置
            }
            
            # 如果配置了 provider 或 china，使用配置创建
            if translator_config["provider"] or translator_config["china"]:
                self._translator = create_translator(translator_config)
            else:
                # 尝试从环境变量自动检测
                self._translator = create_translator()
        else:
            self._translator = None
        
        # 记录翻译器状态
        logger.info(f"🎙️ TTSManager initialized with provider: {self.current_provider.name}")
        if self._translator and self._translator.is_available():
            provider_parts = []
            if self._translator.ai_translator:
                provider_parts.append(self._translator.ai_translator.provider)
            if self._translator.china_translator and self._translator.china_translator.is_available():
                china_names = [t.__class__.__name__.replace("Translator", "") 
                              for t in self._translator.china_translator.available_translators]
                provider_parts.extend(china_names)
            if not provider_parts:
                provider_parts.append("Google")
            
            logger.info(f"🌐 Auto-translation enabled ({', '.join(provider_parts)})")
        else:
            logger.info("🌐 Auto-translation disabled")
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from config.yaml"""
        try:
            import yaml
            config_path = Path(__file__).parent.parent.parent / "config.yaml"
            if config_path.exists():
                with open(config_path, "r", encoding="utf-8") as f:
                    return yaml.safe_load(f) or {}
        except Exception as e:
            logger.debug(f"Failed to load config: {e}")
        return {}
    
    def _select_provider(self, preferred: str) -> BaseTTSProvider:
        """Select best available provider"""
        # Try preferred first
        if preferred in self.providers:
            provider = self.providers[preferred]
            if provider.is_available():
                return provider
        
        # Fallback to any available
        for name, provider in self.providers.items():
            if provider.is_available():
                return provider
        
        # Last resort: local
        return self.providers["local"]
    
    def set_provider(self, name: str) -> bool:
        """Switch TTS provider"""
        if name not in self.providers:
            logger.error(f"Unknown TTS provider: {name}")
            return False
        
        provider = self.providers[name]
        if not provider.is_available():
            logger.error(f"TTS provider '{name}' is not available")
            return False
        
        self.current_provider = provider
        logger.info(f"🎙️ TTS provider switched to: {name}")
        return True
    
    def get_available_providers(self) -> List[str]:
        """Get list of available provider names"""
        return [name for name, p in self.providers.items() if p.is_available()]
    
    def update_gptsovits_config(self, **kwargs) -> bool:
        """
        更新 GPT-SoVITS 配置
        
        Args:
            api_url: API 地址
            refer_wav_path: 参考音频路径
            prompt_text: 参考音频文本
            text_language: 文本语言
            prompt_language: 参考音频语言
            top_k, top_p, temperature, speed: 生成参数
        
        Returns:
            bool: 是否成功更新
        """
        if "gptsovits" not in self.providers:
            logger.error("GPT-SoVITS provider not available")
            return False
        
        provider = self.providers["gptsovits"]
        if hasattr(provider, 'update_config'):
            provider.update_config(**kwargs)
            return True
        return False
    
    def set_gptsovits_voice(self, refer_wav_path: str, prompt_text: str = None, prompt_language: str = "zh") -> bool:
        """
        设置 GPT-SoVITS 的参考音频（切换音色）
        
        Args:
            refer_wav_path: 参考音频文件路径
            prompt_text: 参考音频对应的文本
            prompt_language: 参考音频语言
        
        Returns:
            bool: 是否成功设置
        """
        return self.update_gptsovits_config(
            refer_wav_path=refer_wav_path,
            prompt_text=prompt_text,
            prompt_language=prompt_language
        )

    def set_gptsovits_proxy_voice(self, voice: str) -> bool:
        """切换 GPT-SoVITS-Proxy 的音色"""
        if "gptsovits_proxy" not in self.providers:
            logger.error("GPT-SoVITS-Proxy provider not available")
            return False
        self.providers["gptsovits_proxy"].voice_id = voice
        return True

    def get_gptsovits_proxy_voices(self) -> List[str]:
        """获取可用的 Proxy 音色列表（需代理服务支持）"""
        return []  # 音色列表由代理服务管理，可扩展为 API 查询

    def set_edge_voice(self, voice: str) -> bool:
        """
        设置 Edge TTS 语音
        
        Args:
            voice: Edge TTS 语音 ID
                  日文语音: ja-JP-NanamiNeural, ja-JP-KeitaNeural, ja-JP-MayuNeural, ja-JP-AoiNeural
                  中文语音: zh-CN-XiaoxiaoNeural, zh-CN-YunjianNeural, zh-CN-YunxiNeural
        
        Returns:
            bool: 是否成功设置
        """
        if "edge" not in self.providers:
            logger.error("Edge TTS provider not available")
            return False
        
        provider = self.providers["edge"]
        if hasattr(provider, 'voice'):
            provider.voice = voice
            logger.info(f"🎙️ Edge TTS voice switched to: {voice}")
            return True
        return False
    
    def set_language(self, lang: str) -> bool:
        """
        快速切换语言设置
        
        Args:
            lang: "zh" (中文), "ja" (日文), "en" (英文)
        
        Returns:
            bool: 是否成功设置
        """
        success = False
        
        # 切换 Edge TTS 语音
        edge_voices = {
            "zh": "zh-CN-XiaoxiaoNeural",
            "ja": "ja-JP-NanamiNeural",
            "en": "en-US-AriaNeural"
        }
        if lang in edge_voices:
            success = self.set_edge_voice(edge_voices[lang]) or success
        
        # 切换 GPT-SoVITS 语言
        if "gptsovits" in self.providers:
            success = self.update_gptsovits_config(
                text_language=lang,
                prompt_language=lang
            ) or success
        
        if success:
            self._current_language = lang
            logger.info(f"🌐 Language switched to: {lang}")
        return success
    
    def set_auto_translate(self, enabled: bool):
        """
        设置是否启用自动翻译
        
        Args:
            enabled: True 启用自动翻译，False 禁用
        """
        self._auto_translate = enabled
        logger.info(f"🌐 Auto-translate: {'enabled' if enabled else 'disabled'}")
    
    async def _translate_text(self, text: str) -> str:
        """
        翻译文本到当前目标语言
        
        Args:
            text: 原始文本
            
        Returns:
            翻译后的文本
        """
        if not self._translator or not self._translator.is_available():
            return text
        
        if not self._auto_translate:
            return text
        
        # 翻译到当前语言
        return await self._translator.translate(text, target_lang=self._current_language)
    
    @staticmethod
    def _clean_for_tts(text: str) -> str:
        """去掉 emoji，保留 CJK、ASCII 和常见标点（与生成脚本保持一致）"""
        import unicodedata
        result = []
        for ch in text:
            if ord(ch) < 0x2000:
                result.append(ch)
            elif unicodedata.category(ch).startswith(('So', 'Sk')):
                continue
            elif 0x1F600 <= ord(ch) <= 0x1FFFF:
                continue
            else:
                result.append(ch)
        return ''.join(result).strip()

    def _cache_path(self, text: str) -> str:
        """Get cached audio path for text (emoji-stripped)"""
        clean = self._clean_for_tts(text)
        h = hashlib.md5(clean.encode('utf-8')).hexdigest()
        return os.path.join(self._cache_dir, f"{h}.wav")

    def _find_cached(self, text: str) -> Optional[str]:
        """Check if pre-cached audio exists"""
        path = self._cache_path(text)
        if os.path.exists(path):
            return path
        return None

    async def speak(self, text: str, voice_id: Optional[str] = None) -> TTSResult:
        """
        Generate and play TTS audio with lip sync
        
        如果启用了自动翻译且当前语言不是中文，会自动翻译文本
        
        Args:
            text: Text to speak (会自动翻译到当前设置的语言)
            voice_id: Optional voice ID override
            
        Returns:
            TTSResult with audio info
        """
        if self._is_speaking:
            logger.warning("TTS already in progress, waiting...")
            # Wait for current to finish
            while self._is_speaking:
                await asyncio.sleep(0.1)
        
        # 翻译文本（如果需要）
        original_text = text
        translated_text = await self._translate_text(text)

        if translated_text != original_text:
            logger.info(f"🌐 原文: '{original_text[:50]}...'")
            logger.info(f"🌐 译文: '{translated_text[:50]}...'")

        # 优先从缓存读取
        cached_path = self._find_cached(translated_text)
        if cached_path:
            logger.info(f"📦 使用缓存音频: {translated_text[:30]}...")
            self._is_speaking = True
            self.tts_started.emit(translated_text)
            try:
                if cached_path:
                    self._temp_files.append(cached_path)
                    self._current_audio_path = cached_path
                    self._amplitude_data = self.audio_analyzer.analyze_amplitude(cached_path, 0)
                    self.audio_amplitude.emit(self._amplitude_data)
                await self._play_audio(cached_path)
                return TTSResult(audio_path=cached_path, text=text,
                                 duration_ms=int(self._amplitude_data.__len__() * 1000 / 30)
                                 if self._amplitude_data else 2000,
                                 sample_rate=24000, success=True)
            except Exception as e:
                logger.error(f"❌ 缓存播放失败: {e}")
                self._is_speaking = False
                self.tts_finished.emit()
                return TTSResult(audio_path="", text=text, duration_ms=0,
                                 sample_rate=24000, success=False, error=str(e))
            finally:
                self._is_speaking = False
                self.tts_finished.emit()

        self._is_speaking = True
        self.tts_started.emit(translated_text)
        
        try:
            # Generate audio with translated text
            result = await self.current_provider.speak(translated_text, voice_id)

            # Fallback: if current provider fails, try edge
            if not result.success and self.current_provider.name != "Edge":
                fallback = self.providers.get("edge")
                if fallback and fallback.is_available():
                    logger.warning(f"⚠️ {self.current_provider.name} failed, falling back to Edge TTS")
                    self.current_provider = fallback
                    result = await fallback.speak(translated_text, voice_id)
            
            if not result.success:
                self.tts_error.emit(result.error or "Unknown TTS error")
                self._is_speaking = False
                self.tts_finished.emit()
                return result
            
            # Track temp file for cleanup
            if result.audio_path:
                # Save to cache for future use
                try:
                    cache_path = self._cache_path(translated_text)
                    os.makedirs(os.path.dirname(cache_path), exist_ok=True)
                    import shutil
                    shutil.copy2(result.audio_path, cache_path)
                    logger.debug(f"📦 音频已缓存: {translated_text[:20]}...")
                except Exception as e:
                    logger.debug(f"缓存保存失败(不影响播放): {e}")

                self._temp_files.append(result.audio_path)
                self._current_audio_path = result.audio_path
                
                # Analyze audio for lip sync
                logger.info("🔊 Analyzing audio for lip sync...")
                self._amplitude_data = self.audio_analyzer.analyze_amplitude(result.audio_path, result.duration_ms)
                self.audio_amplitude.emit(self._amplitude_data)
            
            # Play audio
            await self._play_audio(result.audio_path)
            
            return result
            
        except Exception as e:
            logger.error(f"❌ TTS speak error: {e}")
            self.tts_error.emit(str(e))
            self._is_speaking = False
            self.tts_finished.emit()
            return TTSResult(
                audio_path="",
                text=text,
                duration_ms=0,
                sample_rate=24000,
                success=False,
                error=str(e)
            )
    
    async def _play_audio(self, audio_path: str):
        """Play audio file with lip sync - no terminal windows"""
        if not audio_path or not os.path.exists(audio_path):
            logger.warning("No audio file to play")
            self._is_speaking = False
            self.tts_finished.emit()
            return
        
        self._current_frame = 0
        
        # Start lip sync timer (30fps = 33ms per frame) - MUST BE IN MAIN THREAD
        if self._amplitude_data:
            from PyQt6.QtCore import QMetaObject, Qt, Q_ARG
            QMetaObject.invokeMethod(self._playback_timer, "start", Qt.ConnectionType.QueuedConnection, Q_ARG(int, 33))
        
        # Play audio using system player (no terminal windows)
        try:
            import platform as pf
            if pf.system() == 'Darwin':
                # macOS: use afplay
                process = await asyncio.create_subprocess_exec(
                    "afplay", audio_path,
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.DEVNULL
                )
                await process.communicate()
            elif pf.system() == 'Windows':
                # Windows: use pygame (no console window)
                try:
                    import pygame
                    if not pygame.mixer.get_init():
                        pygame.mixer.init(frequency=24000)
                    pygame.mixer.music.load(audio_path)
                    pygame.mixer.music.play()
                    while pygame.mixer.music.get_busy():
                        await asyncio.sleep(0.05)
                except Exception as e:
                    logger.warning(f"Pygame playback failed: {e}, trying fallback")
                    # Fallback: use PowerShell MediaPlayer (hidden window)
                    process = await asyncio.create_subprocess_exec(
                        "powershell", "-c", f"(New-Object Media.SoundPlayer '{audio_path}').PlaySync()",
                        stdout=asyncio.subprocess.DEVNULL,
                        stderr=asyncio.subprocess.DEVNULL,
                        creationflags=subprocess.CREATE_NO_WINDOW
                    )
                    await process.communicate()
            else:
                # Linux: use ffplay or similar
                process = await asyncio.create_subprocess_exec(
                    "ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", audio_path,
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.DEVNULL
                )
                await process.communicate()
                
        except Exception as e:
            logger.error(f"❌ Audio playback error: {e}")
        finally:
            # Stop lip sync
            from PyQt6.QtCore import QMetaObject, Qt
            QMetaObject.invokeMethod(self._playback_timer, "stop", Qt.ConnectionType.QueuedConnection)
            self.lip_sync_frame.emit(0.0)  # Close mouth
            self._is_speaking = False
            self.tts_finished.emit()
    
    def _on_playback_frame(self):
        """Called every frame during audio playback for lip sync"""
        if not self._amplitude_data:
            return
        
        if self._current_frame < len(self._amplitude_data):
            amplitude = self._amplitude_data[self._current_frame]
            
            # 🚨 【关键优化】：使用非线性映射和阈值优化口型同步
            # 1. 添加阈值：低于 0.15 的振幅视为静音（嘴巴完全闭合）
            # 2. 使用幂函数曲线：增强大声时的开口度，减小微声时的开口度
            threshold = 0.15
            if amplitude < threshold:
                mouth_open = 0.0
            else:
                # 归一化到 [0, 1] 范围
                normalized = (amplitude - threshold) / (1.0 - threshold)
                # 使用指数 1.8 区分轻声和无声
                mouth_open = min(normalized ** 1.8 * 1.2, 1.0)
                
            self.lip_sync_frame.emit(mouth_open)
            self._current_frame += 1
        else:
            # End of audio
            self.lip_sync_frame.emit(0.0)
    
    def speak_sync(self, text: str, voice_id: Optional[str] = None) -> TTSResult:
        """Synchronous wrapper for speak()"""
        return asyncio.run(self.speak(text, voice_id))
    
    def is_speaking(self) -> bool:
        """Check if currently speaking"""
        return self._is_speaking
    
    def stop(self):
        """Stop current TTS playback"""
        from PyQt6.QtCore import QMetaObject, Qt
        QMetaObject.invokeMethod(self._playback_timer, "stop", Qt.ConnectionType.QueuedConnection)
        self._is_speaking = False
        self.lip_sync_frame.emit(0.0)
        self.tts_finished.emit()
    
    def cleanup(self):
        """Clean up temp files"""
        self.stop()
        for path in self._temp_files:
            try:
                if os.path.exists(path):
                    os.unlink(path)
                    logger.debug(f"🗑️ Cleaned up temp file: {path}")
            except Exception as e:
                logger.warning(f"Failed to cleanup {path}: {e}")
        self._temp_files.clear()


# Singleton instance
_tts_manager: Optional[TTSManager] = None


def get_tts_manager(preferred_provider: str = "edge") -> TTSManager:
    """Get or create TTSManager singleton"""
    global _tts_manager
    if _tts_manager is None:
        _tts_manager = TTSManager(preferred_provider=preferred_provider)
    return _tts_manager
