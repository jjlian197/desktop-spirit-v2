#!/usr/bin/env python3
"""
GPT-SoVITS TTS Provider (API v2)
支持 GPT-SoVITS api_v2.py 的 API 调用
文档参考: https://github.com/RVC-Boss/GPT-SoVITS
"""

import os
import sys
import asyncio
import tempfile
from typing import Optional, Dict, Any
from pathlib import Path
from dataclasses import dataclass

from src.core.tts_provider_base import BaseTTSProvider, TTSResult
from loguru import logger


@dataclass
class GPTSoVITSConfig:
    """GPT-SoVITS 配置 (适配 api_v2.py)"""
    api_url: str = "http://127.0.0.1:9880/tts"  # GPT-SoVITS 默认端口
    text_language: str = "zh"  # 文本语言: zh, en, ja, auto
    refer_wav_path: Optional[str] = None  # 参考音频路径 (对应 api_v2 的 ref_audio_path)
    prompt_text: Optional[str] = None  # 参考音频文本
    prompt_language: str = "zh"  # 参考音频语言: zh, en, ja
    # api_v2 特有参数
    text_split_method: str = "cut5"  # 文本分割方法: cut0, cut1, cut2, cut3, cut4, cut5
    batch_size: int = 1  # 批次大小
    media_type: str = "wav"  # 音频格式: wav, mp3, ogg
    streaming_mode: bool = False  # 是否流式输出
    # 旧版参数（api_v2 可能不支持）
    top_k: int = 20
    top_p: float = 0.6
    temperature: float = 0.6
    speed: float = 1.0  # 语速


class GPTSoVITSProvider(BaseTTSProvider):
    """
    GPT-SoVITS TTS Provider (API v2)
    支持通过 API 调用 GPT-SoVITS api_v2.py 生成高质量语音
    """
    
    def __init__(self, config: Optional[GPTSoVITSConfig] = None):
        super().__init__("GPTSoVITS")
        self.config = config or GPTSoVITSConfig()
        self._initialized = False
        self._check_availability()
    
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
            voice_id: 可选，可以传入参考音频路径 (ref_audio_path)
        
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
            
            # 确定参考音频路径
            ref_audio_path = None
            if voice_id and os.path.exists(voice_id):
                ref_audio_path = voice_id
            elif self.config.refer_wav_path and os.path.exists(self.config.refer_wav_path):
                ref_audio_path = self.config.refer_wav_path
            
            if not ref_audio_path:
                logger.warning("⚠️ GPT-SoVITS: No reference audio provided!")
                return TTSResult(
                    audio_path="",
                    text=text,
                    duration_ms=0,
                    sample_rate=32000,
                    success=False,
                    error="GPT-SoVITS api_v2 requires reference audio (ref_audio_path)"
                )
            
            # 构建 api_v2 查询参数
            params = {
                "text": text,
                "text_lang": self.config.text_language,
                "ref_audio_path": ref_audio_path,
                "prompt_lang": self.config.prompt_language,
                "text_split_method": self.config.text_split_method,
                "batch_size": self.config.batch_size,
                "media_type": self.config.media_type,
                "streaming_mode": str(self.config.streaming_mode).lower(),
            }
            
            # 添加 prompt_text（如果配置了）
            if self.config.prompt_text:
                params["prompt_text"] = self.config.prompt_text
            
            logger.info(f"🎙️ GPT-SoVITS: synthesizing '{text[:30]}...'")
            logger.debug(f"🎙️ GPT-SoVITS params: {params}")
            
            # 调用 GPT-SoVITS api_v2 (GET 请求)
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self.config.api_url,
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=120)  # api_v2 可能需要较长时间
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(f"GPT-SoVITS API error {response.status}: {error_text}")
                    
                    # 保存音频数据
                    audio_data = await response.read()
                    with open(output_path, "wb") as f:
                        f.write(audio_data)
            
            # 计算音频时长
            duration_ms = await self._get_audio_duration(output_path, text)
            
            logger.info(f"✅ GPT-SoVITS: audio generated ({duration_ms:.0f}ms)")
            
            return TTSResult(
                audio_path=output_path,
                text=text,
                duration_ms=duration_ms,
                sample_rate=32000,  # GPT-SoVITS 默认采样率
                success=True
            )
            
        except asyncio.TimeoutError:
            logger.error("❌ GPT-SoVITS: Request timeout")
            self._cleanup_file(output_path)
            return TTSResult(
                audio_path="",
                text=text,
                duration_ms=0,
                sample_rate=32000,
                success=False,
                error="GPT-SoVITS request timeout"
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
        """获取音频时长（毫秒）"""
        try:
            import wave
            with wave.open(audio_path, 'rb') as wav:
                frames = wav.getnframes()
                rate = wav.getframerate()
                return (frames / rate) * 1000
        except:
            # 回退：根据文本长度估算
            return len(text) * 220  # GPT-SoVITS 通常语速稍慢
    
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
            # 尝试一个简单的 GET 请求检查服务是否在线
            base_url = self.config.api_url.rsplit('/', 1)[0]
            async with aiohttp.ClientSession() as session:
                async with session.get(base_url, timeout=5) as response:
                    return response.status < 500
        except:
            return False


class GPTSoVITSProviderSimple(GPTSoVITSProvider):
    """
    简化版 GPT-SoVITS Provider
    使用更简单的 API 调用方式（适用于一些简化版的 GPT-SoVITS 部署）
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
        self.name = "GPTSoVITS-Simple"
