#!/usr/bin/env python3
"""
Sherry STT 子进程 - 在独立进程中运行 Whisper 识别
避免与 Qt/WebEngine 的 GL 上下文冲突
"""

import logging
import os
import sys
import tempfile
import threading
import time
import wave
import json
import struct

# 设置 UTF-8 输出
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# 从父进程接收配置
import argparse
parser = argparse.ArgumentParser()
parser.add_argument("--lang", default="zh")
parser.add_argument("--energy", type=int, default=300)
parser.add_argument("--log-fd", type=int, default=-1)  # 日志管道的文件描述符
args, _ = parser.parse_known_args()

# 简单的日志输出到 stderr（会被父进程捕获）
def log(msg):
    print(f"[STT-SUB] {msg}", file=sys.stderr, flush=True)

log(f"子进程启动, lang={args.lang}, energy={args.energy}")

# STDOUT 用于 IPC：每行一个 JSON 消息
# 消息类型：
#   {"type": "ready"}              - 模型加载完成
#   {"type": "transcript", "text": "..."}  - 识别结果
#   {"type": "error", "msg": "..."} - 错误
#   {"type": "listening"}           - 开始监听
#   {"type": "stopped"}             - 停止监听
#   {"type": "audio_device", "id": N, "name": "..."} - 音频设备信息

# STDIN 用于接收命令：
#   "start\n" - 开始监听
#   "stop\n"  - 停止监听
#   "lang zh\n" - 设置语言

# === 模型加载 ===
_model = None
_audio = None
_stream = None
_is_listening = False
_stop_event = threading.Event()
pyaudio = None  # 由 _init_audio 填充

def _load_model():
    global _model
    log("加载 Whisper 模型...")
    try:
        from faster_whisper import WhisperModel
        _model = WhisperModel("base", device="cpu", compute_type="int8")
        log("模型加载完成")
        _send({"type": "ready", "success": True})
    except Exception as e:
        log(f"模型加载失败: {e}")
        _send({"type": "ready", "success": False, "error": str(e)})

def _send(msg):
    """通过 stdout 发送 JSON 消息"""
    try:
        line = json.dumps(msg, ensure_ascii=False)
        sys.stdout.write(line + "\n")
        sys.stdout.flush()
    except Exception as e:
        log(f"_send 失败: {e}")

def _audio_energy(frames):
    import numpy as np
    audio_data = np.frombuffer(b''.join(frames), dtype=np.int16)
    return np.abs(audio_data).mean()

def _init_audio():
    global _audio, pyaudio
    if _audio is not None:
        return _audio
    import pyaudio as _pa
    pyaudio = _pa
    _audio = pyaudio.PyAudio()

    # 打印默认输入设备
    try:
        default_input = _audio.get_default_input_device_info()
        log(f"默认输入设备: [{default_input['index']}] {default_input['name']} "
            f"(rate={default_input['defaultSampleRate']}, "
            f"channels={default_input['maxInputChannels']})")
    except Exception as e:
        log(f"获取默认输入设备失败: {e}")

    # 枚举所有输入设备
    for i in range(_audio.get_device_count()):
        dev = _audio.get_device_info_by_index(i)
        if dev.get('maxInputChannels', 0) > 0:
            log(f"输入设备 [{i}]: {dev['name']} (in={dev['maxInputChannels']}, rate={dev['defaultSampleRate']})")

    return _audio

def _listen_loop():
    global _is_listening, _stream
    log("_listen_loop 开始")
    _send({"type": "listening"})

    p = _init_audio()
    CHUNK = 1024
    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    RATE = 16000
    RECORD_SECONDS = 5
    ENERGY = args.energy
    LANG = args.lang

    temp_file = os.path.join(tempfile.gettempdir(), "sherry_stt.wav")

    try:
        _stream = p.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=RATE,
            input=True,
            frames_per_buffer=CHUNK
        )
        log("音频流已打开")
    except Exception as e:
        log(f"打开音频流失败: {e}")
        _send({"type": "error", "msg": f"音频流失败: {e}"})
        return

    silent_chunks = 0
    while _is_listening and not _stop_event.is_set():
        try:
            frames = []
            for _ in range(int(RATE / CHUNK * RECORD_SECONDS)):
                if not _is_listening:
                    break
                data = _stream.read(CHUNK, exception_on_overflow=False)
                frames.append(data)

            if not _is_listening:
                break

            # 能量检测 + 日志
            energy = _audio_energy(frames)

            if energy < ENERGY:
                silent_chunks += 1
                if silent_chunks % 3 == 1:
                    log(f"音频能量: {energy:.1f} < {ENERGY} (静默中)")
                continue
            else:
                log(f"🎵 检测到声音！能量: {energy:.1f} >= {ENERGY}")
                silent_chunks = 0

            # 保存临时 WAV
            with wave.open(temp_file, 'wb') as wf:
                wf.setnchannels(CHANNELS)
                wf.setsampwidth(p.get_sample_size(FORMAT))
                wf.setframerate(RATE)
                wf.writeframes(b''.join(frames))

            # Whisper 识别
            segments, _ = _model.transcribe(temp_file, language=LANG)
            text = "".join([s.text for s in segments]).strip()

            if text:
                log(f"识别: {text}")
                _send({"type": "transcript", "text": text})

            try:
                os.remove(temp_file)
            except:
                pass

        except Exception as e:
            log(f"录音循环错误: {e}")
            if _is_listening:
                time.sleep(0.5)

    log("_listen_loop 退出")

    # 清理音频
    if _stream:
        try:
            _stream.stop_stream()
            _stream.close()
        except:
            pass
        _stream = None
    if p:
        try:
            p.terminate()
        except:
            pass

def _set_language(lang):
    global args
    lang_map = {"zh": "zh", "en": "en", "ja": "ja", "ko": "ko"}
    args.lang = lang_map.get(lang, lang)
    log(f"语言设置为: {args.lang}")

# === 预加载模型（阻塞启动）===
_load_model()

# === 命令循环 ===
log("进入命令循环，等待命令...")
while True:
    try:
        line = sys.stdin.readline()
        if not line:
            break
        line = line.strip()
        if not line:
            continue

        log(f"收到命令: {line}")

        if line == "start":
            if _is_listening:
                log("已在监听，忽略")
                continue
            if _model is None:
                _send({"type": "error", "msg": "模型未加载"})
                continue
            _is_listening = True
            _stop_event.clear()
            t = threading.Thread(target=_listen_loop, daemon=True)
            t.start()

        elif line == "stop":
            _is_listening = False
            _stop_event.set()
            log("stop 命令已处理")

        elif line.startswith("lang "):
            lang = line.split(" ", 1)[1].strip()
            _set_language(lang)
            _send({"type": "lang_set", "lang": args.lang})

        elif line == "quit":
            log("退出子进程")
            break

    except Exception as e:
        log(f"命令循环错误: {e}")
        break

log("子进程结束")
