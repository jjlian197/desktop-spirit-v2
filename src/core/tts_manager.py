#!/usr/bin/env python3
"""
TTS Manager - Text-to-Speech management with multiple providers
Supports: Edge TTS (default), ElevenLabs, Local TTS
Handles audio playback and lip sync integration
"""

import os
import asyncio
import tempfile
import subprocess
import wave
import struct
import numpy as np
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Callable, List, Dict, Any
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor

from PyQt6.QtCore import QObject, pyqtSignal, QThread, QTimer
from loguru import logger


def is_apple_silicon() -> bool:
    """Check if running on Apple Silicon"""
    import platform
    return platform.machine() == 'arm64' and platform.system() == 'Darwin'


@dataclass
class TTSResult:
    """Result from TTS generation"""
    audio_path: str
    text: str
    duration_ms: float
    sample_rate: int
    success: bool
    error: Optional[str] = None


class BaseTTSProvider(ABC):
    """Base class for TTS providers"""
    
    def __init__(self, name: str):
        self.name = name
        self._initialized = False
    
    @abstractmethod
    async def speak(self, text: str, voice_id: Optional[str] = None) -> TTSResult:
        """Generate and return audio file path"""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if provider is available"""
        pass
    
    async def warmup(self):
        """Warm up the provider (optional)"""
        pass


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
            subprocess.run(["edge-tts", "--version"], 
                         capture_output=True, check=True)
            self._initialized = True
            logger.info("✅ EdgeTTS provider initialized")
        except (subprocess.CalledProcessError, FileNotFoundError):
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
            # Build edge-tts command
            cmd = [
                "edge-tts",
                "--voice", voice,
                "--text", text,
                "--write-media", output_path,
                "--rate", self.rate,
                "--pitch", self.pitch
            ]
            
            # Run edge-tts
            logger.info(f"🎙️ EdgeTTS: generating audio for '{text[:30]}...'")
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                raise Exception(f"EdgeTTS failed: {stderr.decode()}")
            
            # Get audio duration
            duration_ms = await self._get_audio_duration(output_path)
            
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
    
    async def _get_audio_duration(self, audio_path: str) -> float:
        """Get audio duration in milliseconds"""
        try:
            import subprocess
            result = subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries", 
                 "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", audio_path],
                capture_output=True, text=True
            )
            duration_sec = float(result.stdout.strip())
            return duration_sec * 1000
        except:
            # Fallback: estimate based on text length
            return len(text) * 200  # ~200ms per character


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
                
            else:  # Windows or fallback
                # Use say command directly without file output
                # Local TTS on Windows doesn't support file output easily
                cmd = ["say", text]
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                await process.communicate()
                # Return empty path since we played directly
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
    
    def analyze_amplitude(self, audio_path: str) -> List[float]:
        """
        Analyze audio file and return amplitude values per frame
        Returns list of normalized amplitude values (0.0 - 1.0)
        """
        try:
            # Convert to WAV if needed
            wav_path = self._convert_to_wav(audio_path)
            
            # Read WAV file
            with wave.open(wav_path, 'rb') as wav_file:
                n_channels = wav_file.getnchannels()
                sample_width = wav_file.getsampwidth()
                frame_rate = wav_file.getframerate()
                n_frames = wav_file.getnframes()
                
                # Read all frames
                raw_data = wav_file.readframes(n_frames)
                
                # Convert to numpy array
                if sample_width == 2:
                    fmt = f"{n_frames * n_channels}h"
                    samples = np.array(struct.unpack(fmt, raw_data))
                elif sample_width == 1:
                    samples = np.frombuffer(raw_data, dtype=np.uint8)
                    samples = (samples.astype(np.float32) - 128) / 128.0
                else:
                    logger.warning(f"Unsupported sample width: {sample_width}")
                    return []
                
                # Convert to mono
                if n_channels == 2:
                    samples = samples[::2]  # Take left channel
                
                # Calculate samples per frame
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
                    normalized = min(rms / 32768.0 * 8, 1.0)  # Scale up for better sensitivity
                    amplitudes.append(normalized)
                
                # Clean up temp WAV if converted
                if wav_path != audio_path and os.path.exists(wav_path):
                    try:
                        os.unlink(wav_path)
                    except:
                        pass
                
                return amplitudes
                
        except Exception as e:
            logger.error(f"❌ Audio analysis error: {e}")
            return []
    
    def _convert_to_wav(self, audio_path: str) -> str:
        """Convert audio file to WAV format if needed"""
        if audio_path.endswith('.wav'):
            return audio_path
        
        # Convert using ffmpeg
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            wav_path = f.name
        
        try:
            subprocess.run([
                "ffmpeg", "-y", "-i", audio_path,
                "-acodec", "pcm_s16le", "-ar", "24000", "-ac", "1",
                wav_path
            ], capture_output=True, check=True)
            return wav_path
        except Exception as e:
            logger.error(f"FFmpeg conversion failed: {e}")
            # Return original path and hope for the best
            return audio_path


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
        
        # Initialize providers
        self.providers: Dict[str, BaseTTSProvider] = {
            "edge": EdgeTTSProvider(),
            "elevenlabs": ElevenLabsProvider(),
            "local": LocalTTSProvider(),
        }
        
        self.current_provider = self._select_provider(preferred_provider)
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
        
        logger.info(f"🎙️ TTSManager initialized with provider: {self.current_provider.name}")
    
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
    
    async def speak(self, text: str, voice_id: Optional[str] = None) -> TTSResult:
        """
        Generate and play TTS audio with lip sync
        
        Args:
            text: Text to speak
            voice_id: Optional voice ID override
            
        Returns:
            TTSResult with audio info
        """
        if self._is_speaking:
            logger.warning("TTS already in progress, waiting...")
            # Wait for current to finish
            while self._is_speaking:
                await asyncio.sleep(0.1)
        
        self._is_speaking = True
        self.tts_started.emit(text)
        
        try:
            # Generate audio
            result = await self.current_provider.speak(text, voice_id)
            
            if not result.success:
                self.tts_error.emit(result.error or "Unknown TTS error")
                self._is_speaking = False
                self.tts_finished.emit()
                return result
            
            # Track temp file for cleanup
            if result.audio_path:
                self._temp_files.append(result.audio_path)
                self._current_audio_path = result.audio_path
                
                # Analyze audio for lip sync
                logger.info("🔊 Analyzing audio for lip sync...")
                self._amplitude_data = self.audio_analyzer.analyze_amplitude(result.audio_path)
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
        """Play audio file with lip sync"""
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
        
        # Play audio using system player
        try:
            if is_apple_silicon() or os.uname().sysname == 'Darwin':
                # macOS: use afplay
                process = await asyncio.create_subprocess_exec(
                    "afplay", audio_path,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                await process.communicate()
            else:
                # Linux/Windows: use ffplay or similar
                process = await asyncio.create_subprocess_exec(
                    "ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", audio_path,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
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
