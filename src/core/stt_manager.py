#!/usr/bin/env python3
"""
Sherry STT Manager - Whisper 本地语音识别
使用 faster-whisper 进行完全本地离线识别
"""

import logging
import os
import threading
import wave
from typing import Optional, Callable, Dict

logger = logging.getLogger("STTManager")


class STTManager:
    """
    本地语音识别管理器
    使用 faster-whisper 进行完全本地离线识别
    """

    def __init__(self, language: str = "zh"):
        self.language = language
        self.is_listening = False
        self._stop_event = threading.Event()
        self._listen_thread: Optional[threading.Thread] = None

        self.on_transcript: Optional[Callable[[str, bool], None]] = None
        self.on_error: Optional[Callable[[str], None]] = None
        self.on_ready: Optional[Callable[[], None]] = None

        self._model = None
        self._check_dependencies()

    def _check_dependencies(self):
        """检查依赖"""
        try:
            from faster_whisper import WhisperModel
            logger.info("✅ faster-whisper 已安装")
            self._load_model()
        except ImportError as e:
            logger.error(f"❌ 缺少 faster-whisper: {e}")
            if self.on_error:
                self.on_error("请安装: pip install faster-whisper")

    def _load_model(self):
        """加载 Whisper 模型"""
        try:
            from faster_whisper import WhisperModel
            # 使用 base 模型，平衡速度和准确率
            self._model = WhisperModel("base", device="cpu", compute_type="int8")
            logger.info("✅ Whisper 模型加载完成 (base)")
        except Exception as e:
            logger.error(f"❌ 模型加载失败: {e}")
            if self.on_error:
                self.on_error(f"模型加载失败: {e}")

    def set_language(self, language: str) -> bool:
        """设置识别语言"""
        lang_map = {
            "zh": "zh",
            "zh-CN": "zh",
            "en": "en",
            "en-US": "en",
            "ja": "ja",
            "ja-JP": "ja",
        }
        self.language = lang_map.get(language, "zh")
        logger.info(f"🌐 STT 语言: {self.language} (Whisper)")
        return True

    def get_available_languages(self) -> Dict[str, str]:
        return {
            "zh": "中文",
            "zh-CN": "中文 (简体)",
            "en": "English",
            "en-US": "English (US)",
            "ja": "日本語",
        }

    def start_listening(self) -> bool:
        """开始监听"""
        if self.is_listening:
            return False

        if not self._model:
            if self.on_error:
                self.on_error("Whisper 模型未加载")
            return False

        self.is_listening = True
        self._stop_event.clear()

        self._listen_thread = threading.Thread(target=self._listen_loop, daemon=True)
        self._listen_thread.start()

        logger.info("🎤 开始监听 (Whisper 本地识别)...")
        if self.on_ready:
            self.on_ready()

        return True

    def stop_listening(self):
        """停止监听"""
        if not self.is_listening:
            return

        self.is_listening = False
        self._stop_event.set()

        if self._listen_thread:
            self._listen_thread.join(timeout=2)

        logger.info("🎤 停止监听")

    def _audio_energy(self, frames) -> float:
        """计算音频能量"""
        import numpy as np
        audio_data = np.frombuffer(b''.join(frames), dtype=np.int16)
        return np.abs(audio_data).mean()

    def _listen_loop(self):
        """监听循环 - 录音并使用 Whisper 识别"""
        import pyaudio
        import wave

        CHUNK = 1024
        FORMAT = pyaudio.paInt16
        CHANNELS = 1
        RATE = 16000
        RECORD_SECONDS = 5
        ENERGY_THRESHOLD = 1000  # 能量阈值，低于此值视为噪声（调高减少误触发）

        try:
            logger.info("🎤 初始化 PyAudio...")
            p = pyaudio.PyAudio()
            logger.info("🎤 打开音频流...")
            stream = p.open(
                format=FORMAT,
                channels=CHANNELS,
                rate=RATE,
                input=True,
                frames_per_buffer=CHUNK
            )
            logger.info("🎤 录音中，等待说话...")

            while self.is_listening and not self._stop_event.is_set():
                try:
                    # 录音
                    frames = []
                    for _ in range(0, int(RATE / CHUNK * RECORD_SECONDS)):
                        if not self.is_listening:
                            break
                        data = stream.read(CHUNK, exception_on_overflow=False)
                        frames.append(data)

                    if not self.is_listening:
                        break

                    # 检查音频能量，过低则跳过（噪声过滤）
                    energy = self._audio_energy(frames)
                    if energy < ENERGY_THRESHOLD:
                        continue

                    # 保存为临时 WAV 文件
                    temp_file = "/tmp/sherry_stt.wav"
                    with wave.open(temp_file, 'wb') as wf:
                        wf.setnchannels(CHANNELS)
                        wf.setsampwidth(p.get_sample_size(FORMAT))
                        wf.setframerate(RATE)
                        wf.writeframes(b''.join(frames))

                    # 使用 Whisper 识别（不使用 VAD，减少延迟）
                    segments, _ = self._model.transcribe(
                        temp_file,
                        language=self.language
                    )

                    text = "".join([seg.text for seg in segments]).strip()

                    if text and self.is_listening:
                        logger.info(f"🎤 识别: {text}")
                        if self.on_transcript:
                            self.on_transcript(text, True)

                    # 清理临时文件
                    try:
                        os.remove(temp_file)
                    except:
                        pass

                except Exception as e:
                    logger.error(f"识别循环错误: {e}")

            stream.stop_stream()
            stream.close()
            p.terminate()

        except ImportError as e:
            logger.error(f"缺少 PyAudio: {e}")
            if self.on_error:
                self.on_error(f"缺少 PyAudio: {e}")
        except Exception as e:
            logger.error(f"录音错误: {e}")
            if self.on_error:
                self.on_error(str(e))


def create_stt_provider(**kwargs) -> STTManager:
    return STTManager(**kwargs)