# GPT-SoVITS 接入指南

本指南介绍如何在雪莉桌面精灵中接入 GPT-SoVITS 作为自定义 TTS 引擎。

## 前置要求

1. 安装依赖：
```bash
pip install aiohttp pyyaml
```

2. 启动 GPT-SoVITS API 服务：
```bash
# 在 GPT-SoVITS 目录下启动 API 服务
python api.py -s "path/to/speaker.wav" -g "path/to/gpt_model" -sr "path/to/sovits_model"
```

默认 API 地址为 `http://127.0.0.1:9880/tts`

## 启用 GPT-SoVITS

### 方式一：通过配置文件启用

编辑 `config.yaml`：

```yaml
tts:
  # 默认使用 GPT-SoVITS
  default_provider: "gptsovits"
  
  gptsovits:
    enabled: true  # 启用 GPT-SoVITS
    api_url: "http://127.0.0.1:9880/tts"  # API 地址
    text_language: "zh"  # 文本语言: zh, en, ja, all_zh, all_ja
    
    # 参考音频配置（用于音色克隆）
    refer_wav_path: "C:/path/to/reference.wav"  # 参考音频路径
    prompt_text: "参考音频对应的文本内容"  # 参考音频文本
    prompt_language: "zh"  # 参考音频语言
    
    # 生成参数
    top_k: 20
    top_p: 0.6
    temperature: 0.6
    speed: 1.0  # 语速
```

### 方式二：运行时动态切换

通过 WebSocket 发送命令切换：

```python
import asyncio
import websockets
import json

async def switch_to_gptsovits():
    uri = "ws://127.0.0.1:8765/sprite"
    async with websockets.connect(uri) as ws:
        # 切换到 GPT-SoVITS
        await ws.send(json.dumps({
            "type": "tts_provider",
            "data": {"provider": "gptsovits"}
        }))
        print(await ws.recv())

asyncio.run(switch_to_gptsovits())
```

## 动态配置 GPT-SoVITS

### 更新 API 配置

```python
await ws.send(json.dumps({
    "type": "gptsovits_config",
    "data": {
        "api_url": "http://127.0.0.1:9880/tts",
        "text_language": "zh",
        "top_k": 20,
        "top_p": 0.6,
        "temperature": 0.6,
        "speed": 1.0
    }
}))
```

### 切换音色（参考音频）

```python
await ws.send(json.dumps({
    "type": "gptsovits_config",
    "data": {
        "refer_wav_path": "C:/voices/character1.wav",
        "prompt_text": "这是参考音频的文本内容",
        "prompt_language": "zh"
    }
}))
```

## 使用 GPT-SoVITS 说话

### 方式一：WebSocket 命令

```python
await ws.send(json.dumps({
    "type": "speak",
    "data": {
        "text": "你好，我是雪莉！",
        "provider": "gptsovits",  # 指定使用 GPT-SoVITS
        # 也可以不传 provider，使用当前默认 provider
    }
}))
```

### 方式二：指定参考音频说话

```python
await ws.send(json.dumps({
    "type": "speak",
    "data": {
        "text": "你好，我是雪莉！",
        "voice": "C:/voices/character1.wav"  # 作为 refer_wav_path 传入
    }
}))
```

## 配置参数说明

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `api_url` | string | `http://127.0.0.1:9880/tts` | GPT-SoVITS API 地址 |
| `text_language` | string | `zh` | 待合成文本的语言：zh(中文), en(英文), ja(日文), all_zh(全中文), all_ja(全日文) |
| `refer_wav_path` | string | null | 参考音频路径（用于音色克隆） |
| `prompt_text` | string | null | 参考音频对应的文本 |
| `prompt_language` | string | `zh` | 参考音频的语言 |
| `top_k` | int | 20 | 采样 top_k |
| `top_p` | float | 0.6 | 采样 top_p |
| `temperature` | float | 0.6 | 采样温度 |
| `speed` | float | 1.0 | 语速，1.0 为正常速度 |

## 故障排除

### 1. GPT-SoVITS 服务未启动

检查 GPT-SoVITS API 是否正常运行：
```bash
curl http://127.0.0.1:9880
```

### 2. 参考音频路径问题

- Windows 路径使用正斜杠 `/` 或双反斜杠 `\\`
- 确保路径存在且可访问

### 3. 语言设置不匹配

确保 `text_language` 与实际文本语言匹配：
- 纯中文：`zh` 或 `all_zh`
- 纯英文：`en`
- 纯日文：`ja` 或 `all_ja`
- 中日混合：`zh`

### 4. 查看日志

```bash
tail -f ~/.sherry/sprite.log
```

## 完整示例

```python
import asyncio
import websockets
import json

async def demo():
    uri = "ws://127.0.0.1:8765/sprite"
    async with websockets.connect(uri) as ws:
        # 1. 切换到 GPT-SoVITS
        await ws.send(json.dumps({
            "type": "tts_provider",
            "data": {"provider": "gptsovits"}
        }))
        print("Switch:", await ws.recv())
        
        # 2. 配置音色
        await ws.send(json.dumps({
            "type": "gptsovits_config",
            "data": {
                "refer_wav_path": "C:/GPT-SoVITS/voices/sherry.wav",
                "prompt_text": "你好，我是雪莉，很高兴认识你。",
                "prompt_language": "zh"
            }
        }))
        print("Config:", await ws.recv())
        
        # 3. 说话
        await ws.send(json.dumps({
            "type": "speak",
            "data": {"text": "主人你好！我是雪莉，终于可以用自己的声音和你交流了！"}
        }))
        print("Speak:", await ws.recv())

asyncio.run(demo())
```

## 注意事项

1. GPT-SoVITS 需要较长时间生成音频（首次调用可能需要 5-10 秒）
2. 确保 GPU 显存充足，或使用 CPU 模式
3. 建议在本地网络环境下使用，延迟更低
