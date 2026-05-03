#!/usr/bin/env python3
"""
Sherry STT Manager - 通过子进程运行 Whisper 识别
主进程不加载 faster-whisper/pyaudio，避免与 Qt/WebEngine 冲突
"""

import json
import logging
import os
import sys
import threading
from pathlib import Path
from typing import Optional, Callable, Dict

logger = logging.getLogger("STTManager")


class STTManager:
    """
    语音识别管理器 - 子进程模式
    Whisper 和 PyAudio 在独立子进程中运行，通过 stdin/stdout JSON 通信
    """

    def __init__(self, language: str = "zh", energy_threshold: int = 300):
        logger.info("[STT] __init__, lang=%s, energy=%d", language, energy_threshold)
        self.language = language
        self.energy_threshold = energy_threshold
        self.is_listening = False

        self.on_transcript: Optional[Callable[[str, bool], None]] = None
        self.on_error: Optional[Callable[[str], None]] = None
        self.on_ready: Optional[Callable[[], None]] = None

        self._process = None
        self._reader_thread: Optional[threading.Thread] = None
        self._model_ready = threading.Event()
        self._model_ok = False
        self._stopping = False

        # 子进程脚本路径
        self._script = str(Path(__file__).parent / "stt_subprocess.py")

    def _start_subprocess(self) -> bool:
        """启动 STT 子进程"""
        if self._process is not None and self._process.poll() is None:
            return True

        logger.info("[STT] 启动子进程: %s", self._script)
        try:
            import subprocess
            self._process = subprocess.Popen(
                [sys.executable, self._script,
                 "--lang", self.language,
                 "--energy", str(self.energy_threshold)],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
            )
            logger.info("[STT] 子进程已启动, PID=%d", self._process.pid)
        except Exception as e:
            logger.error("[STT] 子进程启动失败: %e", e, exc_info=True)
            if self.on_error:
                self.on_error(f"子进程启动失败: {e}")
            return False

        # 启动 stderr 读取线程（日志转发）
        t_err = threading.Thread(target=self._read_stderr, daemon=True)
        t_err.start()

        # 启动 stdout 读取线程（消息处理）
        self._reader_thread = threading.Thread(target=self._read_stdout, daemon=True)
        self._reader_thread.start()

        return True

    def _read_stderr(self):
        """读取子进程 stderr 日志"""
        if not self._process:
            return
        try:
            for line in self._process.stderr:
                if not line:
                    break
                msg = line.decode('utf-8', errors='replace').rstrip()
                if msg:
                    logger.info("[STT-sub] %s", msg)
        except Exception:
            pass

    def _read_stdout(self):
        """读取子进程 stdout 消息"""
        if not self._process:
            return
        try:
            for line in self._process.stdout:
                if not line:
                    break
                raw = line.decode('utf-8', errors='replace').strip()
                if not raw:
                    continue
                try:
                    msg = json.loads(raw)
                except json.JSONDecodeError:
                    logger.warning("[STT] 无法解析消息: %s", raw[:100])
                    continue

                msg_type = msg.get("type", "")
                if msg_type == "ready":
                    self._model_ok = msg.get("success", False)
                    self._model_ready.set()
                    logger.info("[STT] 子进程模型就绪: %s", self._model_ok)
                    if not self._model_ok and self.on_error:
                        self.on_error(msg.get("error", "模型加载失败"))

                elif msg_type == "transcript":
                    text = msg.get("text", "")
                    logger.info("[STT] 识别结果: %s", text)
                    if text and self.on_transcript:
                        try:
                            self.on_transcript(text, True)
                        except Exception as e:
                            logger.error("[STT] on_transcript 回调失败: %s", e)

                elif msg_type == "error":
                    err = msg.get("msg", "")
                    logger.error("[STT] 子进程错误: %s", err)
                    if self.on_error:
                        try:
                            self.on_error(err)
                        except Exception:
                            pass

                elif msg_type == "listening":
                    logger.info("[STT] 子进程已开始监听")

        except Exception as e:
            if not self._stopping:
                logger.error("[STT] stdout 读取异常: %s", e)

    def _send_command(self, cmd: str):
        """向子进程发送命令"""
        if self._process and self._process.poll() is None:
            try:
                self._process.stdin.write((cmd + "\n").encode('utf-8'))
                self._process.stdin.flush()
            except Exception as e:
                logger.error("[STT] 发送命令失败: %s", e)

    def set_language(self, language: str) -> bool:
        """设置识别语言"""
        lang_map = {
            "zh": "zh", "zh-CN": "zh",
            "en": "en", "en-US": "en",
            "ja": "ja", "ja-JP": "ja",
            "ko": "ko",
        }
        self.language = lang_map.get(language, "zh")
        self._send_command(f"lang {self.language}")
        logger.info("[STT] 语言设置为: %s", self.language)
        return True

    def get_available_languages(self) -> Dict[str, str]:
        return {
            "zh": "中文",
            "en": "English",
            "ja": "日本語",
            "ko": "한국어",
        }

    def start_listening(self) -> bool:
        """开始监听"""
        logger.info("[STT] start_listening, is_listening=%s", self.is_listening)

        if self.is_listening:
            return False

        # 启动子进程（如果还没启动）
        if self._process is None or self._process.poll() is not None:
            self._model_ready.clear()
            self._model_ok = False
            if not self._start_subprocess():
                return False

            # 等待模型加载（最多 60 秒）
            logger.info("[STT] 等待子进程模型加载...")
            self._model_ready.wait(timeout=60.0)
            if not self._model_ok:
                logger.error("[STT] 模型加载失败")
                return False
            logger.info("[STT] 模型就绪，发送 start 命令")

        self._send_command("start")
        self.is_listening = True
        logger.info("[STT] 🎤 已发送监听命令")

        if self.on_ready:
            try:
                self.on_ready()
            except Exception:
                pass

        return True

    def stop_listening(self):
        """停止监听"""
        if not self.is_listening:
            return
        logger.info("[STT] 停止监听")
        self.is_listening = False
        self._send_command("stop")

    def cleanup(self):
        """清理子进程"""
        logger.info("[STT] 清理...")
        self._stopping = True
        self.is_listening = False
        if self._process and self._process.poll() is None:
            self._send_command("quit")
            try:
                self._process.wait(timeout=5)
            except Exception:
                self._process.kill()
            logger.info("[STT] 子进程已终止")
        self._process = None


def create_stt_provider(**kwargs) -> STTManager:
    return STTManager(**kwargs)
