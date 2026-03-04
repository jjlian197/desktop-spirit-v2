#!/usr/bin/env python3
"""
TTS Manager - Text-to-Speech management with multiple providers
Supports: Edge TTS (default), ElevenLabs, Local TTS (macOS say)
Handles audio playback and lip sync integration

Architecture:
    BaseTTSProvider (abstract)
    ├── EdgeTTSProvider      # Microsoft Edge TTS (online)
    ├── ElevenLabsProvider   # ElevenLabs API (premium)
    └── LocalTTSProvider     # System TTS (macOS say, Linux espeak)
    
    AudioAnalyzer            # Audio analysis for lip sync
    TTSManager              # Central manager with Qt integration
"""

import os
import asyncio
import tempfile
import subprocess
import wave
import struct
import platform
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Callable, List, Dict, Any
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor

import numpy as np
from PyQt6.QtCore import QObject, pyqtSignal, QTimer, QMetaObject, Qt, Q_ARG
from loguru import logger


# =============================================================================
# Utilities
# =============================================================================

def is_apple_silicon() -> bool:
    """Check if running on Apple Silicon Mac"""
    return platform.machine() == 'arm64' and platform.system() == 'Darwin'


def get_system() -> str:
    """Get current operating system"""
    return platform.system()


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class TTSResult:
    """Result from TTS generation"""
    audio_path: str
    text: str
    duration_ms: float
    sample_rate: int
    success: bool
    error: Optional[str] = None


# =============================================================================
# Base Provider
# =============================================================================

class BaseTTSProvider(ABC):
    """Abstract base class for TTS providers"""
    
    def __init__(self, name: str):
        self.name = name
        self._initialized = False
    
    @abstractmethod
    async def speak(self, text: str, voice_id: Optional[str] = None) -> TTSResult:
        """Generate speech audio from text"""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if provider is available on this system"""
        pass
    
    async def warmup(self):
        """Optional warm-up (e.g., load models)"""
        pass


# =============================================================================
# Provider Implementations
# =============================================================================

class EdgeTTSProvider(BaseTTSProvider):
    """
    Microsoft Edge TTS Provider
    - Free online service
    - Good quality Chinese voice (XiaoxiaoNeural)
    - Requires internet connection
    """
    
    DEFAULT_VOICE = "zh-CN-XiaoxiaoNeural"
    
    def __init__(self, voice: Optional[str] = None, rate: str = "+0%", pitch: str = "+0Hz"):
        super().__init__("EdgeTTS")
        self.voice = voice or self.DEFAULT_VOICE
        self.rate = rate
        self.pitch = pitch
        self._edge_tts_cmd = self._find_edge_tts()
        self._initialized = self._edge_tts_cmd is not None
    
    def _find_edge_tts(self) -> Optional[str]:
        """Find edge-tts executable (venv, PyInstaller bundle, or system PATH)"""
        import sys
        
        # 1. Check PyInstaller bundle (_MEIPASS for onefile, or Resources for .app)
        if hasattr(sys, '_MEIPASS'):
            # Try different locations in bundle
            possible_paths = [
                os.path.join(sys._MEIPASS, 'edge-tts'),
                os.path.join(sys._MEIPASS, '..', 'Resources', 'edge-tts'),  # .app bundle
            ]
            for path in possible_paths:
                path = os.path.normpath(path)
                if os.path.exists(path):
                    try:
                        subprocess.run([path, "--version"], 
                                     capture_output=True, check=True)
                        logger.info(f"✅ EdgeTTS found in bundle: {path}")
                        return path
                    except:
                        pass
        
        # 2. Check macOS .app bundle Resources (when running from .app)
        executable_dir = os.path.dirname(sys.executable)
        possible_app_paths = [
            os.path.join(executable_dir, '..', 'Resources', 'edge-tts'),
            os.path.join(executable_dir, 'edge-tts'),
        ]
        for path in possible_app_paths:
            path = os.path.normpath(path)
            if os.path.exists(path):
                try:
                    subprocess.run([path, "--version"], 
                                 capture_output=True, check=True)
                    logger.info(f"✅ EdgeTTS found in app: {path}")
                    return path
                except:
                    pass
        
        # 3. Check virtual environment
        venv_bin = os.path.dirname(sys.executable)
        venv_path = os.path.join(venv_bin, "edge-tts")
        
        if os.path.exists(venv_path):
            try:
                subprocess.run([venv_path, "--version"], 
                             capture_output=True, check=True)
                logger.info(f"✅ EdgeTTS found in venv: {venv_path}")
                return venv_path
            except subprocess.CalledProcessError:
                pass
        
        # 4. Check system PATH
        try:
            subprocess.run(["edge-tts", "--version"], 
                         capture_output=True, check=True)
            logger.info("✅ EdgeTTS found in PATH")
            return "edge-tts"
        except (subprocess.CalledProcessError, FileNotFoundError):
            logger.warning("⚠️ edge-tts not found")
            return None
    
    def is_available(self) -> bool:
        return self._initialized
    
    async def speak(self, text: str, voice_id: Optional[str] = None) -> TTSResult:
        """Generate audio using edge-tts"""
        if not self._initialized:
            return self._error_result(text, "EdgeTTS not initialized")
        
        voice = voice_id or self.voice
        output_path = self._create_temp_file(".mp3")
        
        try:
            cmd = [
                self._edge_tts_cmd,
                "--voice", voice,
                "--text", text,
                "--write-media", output_path,
                "--rate", self.rate,
                "--pitch", self.pitch
            ]
            
            logger.info(f"🎙️ EdgeTTS: generating audio for '{text[:30]}...'")
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                raise Exception(f"EdgeTTS failed: {stderr.decode()}")
            
            duration_ms = await self._estimate_duration(text, output_path)
            
            return TTSResult(
                audio_path=output_path,
                text=text,
                duration_ms=duration_ms,
                sample_rate=24000,
                success=True
            )
            
        except Exception as e:
            logger.error(f"❌ EdgeTTS error: {e}")
            self._cleanup_file(output_path)
            return self._error_result(text, str(e))
    
    async def _estimate_duration(self, text: str, audio_path: str) -> float:
        """Estimate audio duration (ffprobe or fallback)"""
        try:
            result = subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries", 
                 "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", audio_path],
                capture_output=True, text=True
            )
            return float(result.stdout.strip()) * 1000
        except:
            # Fallback: ~200ms per character for Chinese
            return len(text) * 200
    
    def _create_temp_file(self, suffix: str) -> str:
        """Create temporary file"""
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
            return f.name
    
    def _cleanup_file(self, path: str):
        """Safely delete file"""
        try:
            os.unlink(path)
        except:
            pass
    
    def _error_result(self, text: str, error: str) -> TTSResult:
        """Create error result"""
        return TTSResult(
            audio_path="", text=text, duration_ms=0,
            sample_rate=24000, success=False, error=error
        )


class ElevenLabsProvider(BaseTTSProvider):
    """
    ElevenLabs TTS Provider
    - Premium quality voices
    - Requires API key: ELEVENLABS_API_KEY
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
            return self._error_result(text, "ElevenLabs API key not set")
        
        voice = voice_id or self.voice_id
        output_path = self._create_temp_file(".mp3")
        
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
                        raise Exception(f"API error: {await response.text()}")
                    
                    audio_data = await response.read()
                    with open(output_path, "wb") as f:
                        f.write(audio_data)
            
            # Estimate duration: ~180ms per character
            duration_ms = len(text) * 180
            
            return TTSResult(
                audio_path=output_path,
                text=text,
                duration_ms=duration_ms,
                sample_rate=44100,
                success=True
            )
            
        except Exception as e:
            logger.error(f"❌ ElevenLabs error: {e}")
            self._cleanup_file(output_path)
            return self._error_result(text, str(e))
    
    def _create_temp_file(self, suffix: str) -> str:
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
            return f.name
    
    def _cleanup_file(self, path: str):
        try:
            os.unlink(path)
        except:
            pass
    
    def _error_result(self, text: str, error: str) -> TTSResult:
        return TTSResult(
            audio_path="", text=text, duration_ms=0,
            sample_rate=44100, success=False, error=error
        )


class LocalTTSProvider(BaseTTSProvider):
    """
    Local System TTS Provider
    - macOS: say command
    - Linux: espeak
    - Windows: pyttsx3 (fallback, direct playback)
    """
    
    # macOS Chinese voices (newer macOS versions)
    MACOS_VOICES = {
        "zh_female": "mei-jia",  # Chinese female
        "default": "mei-jia"
    }
    
    def __init__(self):
        super().__init__("LocalTTS")
        self._platform = get_system()
        self._initialized = self._check_availability()
    
    def _check_availability(self) -> bool:
        """Check if local TTS is available"""
        if self._platform == 'Darwin':
            try:
                subprocess.run(["say", "-v", "?"], 
                             capture_output=True, check=True)
                logger.info("✅ LocalTTS available (macOS say)")
                return True
            except:
                return False
        
        elif self._platform == 'Linux':
            try:
                subprocess.run(["which", "espeak"], 
                             capture_output=True, check=True)
                logger.info("✅ LocalTTS available (Linux espeak)")
                return True
            except:
                return False
        
        else:  # Windows
            try:
                import pyttsx3
                logger.info("✅ LocalTTS available (Windows pyttsx3)")
                return True
            except ImportError:
                return False
    
    def is_available(self) -> bool:
        return self._initialized
    
    async def speak(self, text: str, voice_id: Optional[str] = None) -> TTSResult:
        """Generate audio using local TTS"""
        if self._platform == 'Darwin':
            return await self._speak_macos(text, voice_id)
        elif self._platform == 'Linux':
            return await self._speak_linux(text, voice_id)
        else:
            return await self._speak_windows(text)
    
    async def _speak_macos(self, text: str, voice_id: Optional[str]) -> TTSResult:
        """macOS: use say command with AIFF output"""
        output_path = self._create_temp_file(".aiff")
        voice = voice_id or self.MACOS_VOICES["default"]
        
        try:
            cmd = ["say", "-v", voice, "-o", output_path, text]
            logger.info(f"🎙️ LocalTTS (say): '{text[:20]}...'")
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                error = stderr.decode() if stderr else "Unknown error"
                raise Exception(f"say failed: {error}")
            
            duration_ms = len(text) * 200
            
            return TTSResult(
                audio_path=output_path,
                text=text,
                duration_ms=duration_ms,
                sample_rate=22050,
                success=True
            )
            
        except Exception as e:
            logger.error(f"❌ macOS say error: {e}")
            self._cleanup_file(output_path)
            return self._error_result(text, str(e))
    
    async def _speak_linux(self, text: str, voice_id: Optional[str]) -> TTSResult:
        """Linux: use espeak"""
        output_path = self._create_temp_file(".wav")
        
        try:
            cmd = ["espeak", "-w", output_path, "-v", "zh", text]
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await process.communicate()
            
            duration_ms = len(text) * 200
            
            return TTSResult(
                audio_path=output_path,
                text=text,
                duration_ms=duration_ms,
                sample_rate=22050,
                success=True
            )
            
        except Exception as e:
            logger.error(f"❌ espeak error: {e}")
            self._cleanup_file(output_path)
            return self._error_result(text, str(e))
    
    async def _speak_windows(self, text: str) -> TTSResult:
        """Windows: use pyttsx3 (direct playback, no file)"""
        try:
            import pyttsx3
            engine = pyttsx3.init()
            engine.say(text)
            engine.runAndWait()
            
            return TTSResult(
                audio_path="",
                text=text,
                duration_ms=len(text) * 200,
                sample_rate=22050,
                success=True
            )
            
        except Exception as e:
            return self._error_result(text, str(e))
    
    def _create_temp_file(self, suffix: str) -> str:
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
            return f.name
    
    def _cleanup_file(self, path: str):
        try:
            os.unlink(path)
        except:
            pass
    
    def _error_result(self, text: str, error: str) -> TTSResult:
        return TTSResult(
            audio_path="", text=text, duration_ms=0,
            sample_rate=22050, success=False, error=error
        )


# =============================================================================
# Audio Analysis
# =============================================================================

class AudioAnalyzer:
    """
    Audio amplitude analyzer for lip sync using ffmpeg
    
    Flow: any audio -> ffmpeg -> raw PCM -> numpy analysis
    """
    
    def __init__(self, frame_rate: int = 30):
        self.frame_rate = frame_rate
    
    def _find_ffmpeg(self) -> Optional[str]:
        """Find ffmpeg executable"""
        possible_paths = [
            "/opt/homebrew/bin/ffmpeg",  # Apple Silicon Homebrew
            "/usr/local/bin/ffmpeg",     # Intel Homebrew
            "/usr/bin/ffmpeg",
            "ffmpeg"  # PATH
        ]
        for path in possible_paths:
            if path == "ffmpeg" or os.path.exists(path):
                try:
                    subprocess.run([path, "-version"], capture_output=True, check=True)
                    return path
                except:
                    continue
        return None
    
    def analyze(self, audio_path: str) -> List[float]:
        """Analyze audio and return amplitude values per frame (0.0-1.0)"""
        ffmpeg_path = self._find_ffmpeg()
        logger.info(f"🎵 FFmpeg path: {ffmpeg_path}")
        if ffmpeg_path is None:
            logger.warning("⚠️ ffmpeg not found, lip sync disabled")
            return []
        
        try:
            # ffmpeg: convert to 16-bit PCM mono @ 22050Hz
            cmd = [
                ffmpeg_path, "-y", "-i", audio_path,
                "-f", "s16le", "-acodec", "pcm_s16le",
                "-ar", "22050", "-ac", "1", "-"
            ]
            result = subprocess.run(cmd, capture_output=True)
            
            if result.returncode != 0:
                logger.error(f"FFmpeg error: {result.stderr.decode()[:100]}")
                return []
            
            # Convert bytes to numpy array (16-bit signed)
            samples = np.frombuffer(result.stdout, dtype=np.int16)
            
            # Calculate RMS per frame (30fps = ~735 samples/frame @ 22050Hz)
            samples_per_frame = 22050 // self.frame_rate
            n_frames = len(samples) // samples_per_frame
            
            amplitudes = []
            for i in range(n_frames):
                frame = samples[i * samples_per_frame : (i + 1) * samples_per_frame]
                rms = np.sqrt(np.mean(frame.astype(np.float64) ** 2))
                # Normalize: 16-bit max is 32768, scale up for sensitivity
                amplitudes.append(min(rms / 32768.0 * 8, 1.0))
            
            return amplitudes
            
        except Exception as e:
            logger.error(f"Audio analysis error: {e}")
            return []


# =============================================================================
# TTS Manager (Main Class)
# =============================================================================

class TTSManager(QObject):
    """
    Central TTS manager with Qt integration
    
    Signals:
        tts_started(text):      TTS playback started
        tts_finished():         TTS playback finished
        tts_error(error):       TTS error occurred
        lip_sync_frame(value):  Mouth open value (0.0-1.0)
        audio_amplitude(data):  Full amplitude array
    """
    
    # Signals
    tts_started = pyqtSignal(str)
    tts_finished = pyqtSignal()
    tts_error = pyqtSignal(str)
    lip_sync_frame = pyqtSignal(float)
    audio_amplitude = pyqtSignal(list)
    
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
        self._temp_files: List[str] = []
        
        # Timer for lip sync (30fps)
        self._playback_timer = QTimer(self)
        self._playback_timer.timeout.connect(self._on_playback_frame)
        
        logger.info(f"🎙️ TTSManager initialized: {self.current_provider.name}")
    
    # -------------------------------------------------------------------------
    # Provider Management
    # -------------------------------------------------------------------------
    
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
                logger.info(f"🔄 Fallback to {name}")
                return provider
        
        # Last resort: local (may not work but worth a try)
        return self.providers["local"]
    
    def set_provider(self, name: str) -> bool:
        """Switch TTS provider"""
        if name not in self.providers:
            logger.error(f"Unknown TTS provider: {name}")
            return False
        
        provider = self.providers[name]
        if not provider.is_available():
            logger.error(f"TTS provider '{name}' not available")
            return False
        
        self.current_provider = provider
        logger.info(f"🎙️ TTS provider: {name}")
        return True
    
    def get_available_providers(self) -> List[str]:
        """Get list of available provider names"""
        return [name for name, p in self.providers.items() if p.is_available()]
    
    # -------------------------------------------------------------------------
    # Speech Synthesis
    # -------------------------------------------------------------------------
    
    async def speak(self, text: str, voice_id: Optional[str] = None, 
                    use_fallback: bool = True) -> TTSResult:
        """
        Generate and play TTS audio with lip sync
        
        Args:
            text: Text to speak
            voice_id: Optional voice override
            use_fallback: Try local TTS if primary fails
        """
        if self._is_speaking:
            logger.warning("TTS in progress, waiting...")
            while self._is_speaking:
                await asyncio.sleep(0.1)
        
        self._is_speaking = True
        self.tts_started.emit(text)
        
        try:
            # Primary provider
            result = await self.current_provider.speak(text, voice_id)
            
            # Fallback to local if failed
            if not result.success and use_fallback:
                logger.warning("🔄 Primary TTS failed, trying local...")
                local = self.providers.get("local")
                if local and local.is_available():
                    result = await local.speak(text, voice_id)
            
            if not result.success:
                self.tts_error.emit(result.error or "TTS error")
                self._finish_speaking()
                return result
            
            # Track temp file
            if result.audio_path:
                self._temp_files.append(result.audio_path)
                self._current_audio_path = result.audio_path
                
                # Analyze for lip sync
                logger.info(f"🔊 Analyzing audio for lip sync: {result.audio_path}")
                self._amplitude_data = self.audio_analyzer.analyze(result.audio_path)
                logger.info(f"✅ Audio analysis complete: {len(self._amplitude_data)} frames")
                self.audio_amplitude.emit(self._amplitude_data)
            
            # Play audio
            await self._play_audio(result.audio_path)
            
            return result
            
        except Exception as e:
            logger.error(f"❌ TTS error: {e}")
            self.tts_error.emit(str(e))
            self._finish_speaking()
            return TTSResult(
                audio_path="", text=text, duration_ms=0,
                sample_rate=24000, success=False, error=str(e)
            )
    
    def speak_sync(self, text: str, voice_id: Optional[str] = None) -> TTSResult:
        """Synchronous wrapper for speak()"""
        try:
            return asyncio.run(self.speak(text, voice_id))
        except Exception as e:
            logger.error(f"❌ speak_sync error: {e}")
            raise
    
    # -------------------------------------------------------------------------
    # Audio Playback
    # -------------------------------------------------------------------------
    
    async def _play_audio(self, audio_path: str):
        """Play audio file with lip sync"""
        if not audio_path or not os.path.exists(audio_path):
            logger.warning("No audio file to play")
            self._finish_speaking()
            return
        
        self._current_frame = 0
        
        # Start lip sync timer (must be in main thread)
        if self._amplitude_data:
            QMetaObject.invokeMethod(
                self._playback_timer, "start",
                Qt.ConnectionType.QueuedConnection,
                Q_ARG(int, 33)  # 30fps
            )
        
        # Play audio
        logger.info(f"🔊 Playing: {os.path.basename(audio_path)}")
        try:
            await self._play_with_system_player(audio_path)
        except Exception as e:
            logger.error(f"❌ Playback error: {e}")
        finally:
            self._finish_speaking()
    
    async def _play_with_system_player(self, audio_path: str):
        """Play audio using system-native player"""
        system = get_system()
        
        if system == 'Darwin':
            # macOS: afplay (使用完整路径确保打包后也能找到)
            afplay_paths = ["/usr/bin/afplay", "/bin/afplay", "afplay"]
            afplay_cmd = None
            for path in afplay_paths:
                if os.path.exists(path):
                    afplay_cmd = path
                    break
            
            logger.info(f"🎵 afplay path: {afplay_cmd}")
            if afplay_cmd is None:
                logger.error("❌ afplay not found")
                return
            
            process = await asyncio.create_subprocess_exec(
                afplay_cmd, audio_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                stderr_str = stderr.decode() if stderr else "Unknown"
                logger.error(f"❌ afplay failed: {stderr_str}")
        
        else:
            # Linux/Windows: ffplay
            process = await asyncio.create_subprocess_exec(
                "ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", audio_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await process.communicate()
    
    # -------------------------------------------------------------------------
    # Lip Sync
    # -------------------------------------------------------------------------
    
    def _on_playback_frame(self):
        """Called every frame during playback"""
        if not self._amplitude_data:
            return
        
        if self._current_frame < len(self._amplitude_data):
            amplitude = self._amplitude_data[self._current_frame]
            mouth_open = self._amplitude_to_mouth(amplitude)
            self.lip_sync_frame.emit(mouth_open)
            self._current_frame += 1
        else:
            self.lip_sync_frame.emit(0.0)
    
    def _amplitude_to_mouth(self, amplitude: float) -> float:
        """
        Convert amplitude to mouth open value
        Uses non-linear mapping for better lip sync
        """
        threshold = 0.15
        
        if amplitude < threshold:
            return 0.0
        
        # Normalize and apply curve
        normalized = (amplitude - threshold) / (1.0 - threshold)
        return min(normalized ** 1.8 * 1.2, 1.0)
    
    # -------------------------------------------------------------------------
    # State Management
    # -------------------------------------------------------------------------
    
    def _finish_speaking(self):
        """Clean up after speaking"""
        QMetaObject.invokeMethod(
            self._playback_timer, "stop",
            Qt.ConnectionType.QueuedConnection
        )
        self.lip_sync_frame.emit(0.0)
        self._is_speaking = False
        self.tts_finished.emit()
    
    def is_speaking(self) -> bool:
        """Check if currently speaking"""
        return self._is_speaking
    
    def stop(self):
        """Stop current playback"""
        QMetaObject.invokeMethod(
            self._playback_timer, "stop",
            Qt.ConnectionType.QueuedConnection
        )
        self._is_speaking = False
        self.lip_sync_frame.emit(0.0)
        self.tts_finished.emit()
    
    # -------------------------------------------------------------------------
    # Cleanup
    # -------------------------------------------------------------------------
    
    def cleanup(self):
        """Clean up temp files"""
        self.stop()
        for path in self._temp_files:
            try:
                if os.path.exists(path):
                    os.unlink(path)
                    logger.debug(f"🗑️ Cleaned: {path}")
            except Exception as e:
                logger.warning(f"Cleanup failed: {e}")
        self._temp_files.clear()


# =============================================================================
# Singleton
# =============================================================================

_tts_manager: Optional[TTSManager] = None


def get_tts_manager(preferred_provider: str = "edge") -> TTSManager:
    """Get or create TTSManager singleton"""
    global _tts_manager
    if _tts_manager is None:
        _tts_manager = TTSManager(preferred_provider=preferred_provider)
    return _tts_manager
