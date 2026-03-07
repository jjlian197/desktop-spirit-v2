# GPT-SoVITS 本地部署使用指南

本指南介绍如何将本地部署的 GPT-SoVITS 接入雪莉桌面精灵。

## 目录

1. [启动 GPT-SoVITS API](#1-启动-gpt-sovits-api)
2. [配置雪莉使用本地 GPT-SoVITS](#2-配置雪莉使用本地-gpt-sovits)
3. [准备参考音频](#3-准备参考音频)
4. [测试与故障排除](#4-测试与故障排除)

---

## 1. 启动 GPT-SoVITS API

### 1.1 找到 GPT-SoVITS 目录

假设你的 GPT-SoVITS 安装在：
```
C:\GPT-SoVITS
```

### 1.2 启动 API 服务

打开命令行（CMD 或 PowerShell），进入 GPT-SoVITS 目录：

```powershell
cd C:\GPT-SoVITS
```

#### 方式一：使用预训练模型（推荐新手）

```powershell
# 使用默认模型启动 API
python api.py

# 或者指定参数启动
python api.py -dr "参考音频.wav" -dt "参考音频的文本" -dl "zh"
```

#### 方式二：使用自己的训练模型

```powershell
# 指定 GPT 和 SoVITS 模型路径
python api.py \
  -s "C:/GPT-SoVITS/GPT_weights/your_model-e15.ckpt" \
  -g "C:/GPT-SoVITS/SoVITS_weights/your_model_e8_s104.pth"
```

参数说明：
- `-s` 或 `--gpt_path`: GPT 模型路径
- `-g` 或 `--sovits_path`: SoVITS 模型路径
- `-dr` 或 `--default_refer_path`: 默认参考音频路径
- `-dt` 或 `--default_refer_text`: 默认参考音频文本
- `-dl` 或 `--default_refer_language`: 默认参考音频语言 (zh/en/ja)

### 1.3 验证 API 是否启动

打开浏览器访问：
```
http://127.0.0.1:9880
```

或命令行测试：
```powershell
curl http://127.0.0.1:9880
```

如果返回类似 `"GPT-SoVITS API is running"` 的响应，说明启动成功。

---

## 2. 配置雪莉使用本地 GPT-SoVITS

### 2.1 修改 config.yaml

编辑 `C:\Users\lianj\Python\desktop-spirit-v2-windows\config.yaml`：

```yaml
tts:
  # 默认使用 GPT-SoVITS
  default_provider: "gptsovits"
  
  gptsovits:
    enabled: true
    
    # 本地 GPT-SoVITS API 地址
    api_url: "http://127.0.0.1:9880/tts"
    
    # 文本语言 (根据你的内容选择)
    # zh = 中文, en = 英文, ja = 日文
    # all_zh = 全中文, all_ja = 全日文
    text_language: "zh"
    
    # 参考音频配置（用于音色克隆）
    # Windows 路径使用正斜杠 / 或双反斜杠 \\
    refer_wav_path: "C:/GPT-SoVITS/voices/sherry_reference.wav"
    prompt_text: "你好，我是雪莉，很高兴能和你聊天。"
    prompt_language: "zh"
    
    # 生成参数（可调）
    top_k: 20          # 越大生成越多样，越小越稳定
    top_p: 0.6         # 采样阈值
    temperature: 0.6   # 随机性，越高越有变化
    speed: 1.0         # 语速，1.0 = 正常
```

### 2.2 启动雪莉

```powershell
cd C:\Users\lianj\Python\desktop-spirit-v2-windows
python start_windows.py
```

---

## 3. 准备参考音频

参考音频（音色样本）对效果影响很大，以下是准备建议：

### 3.1 音频要求

| 参数 | 建议值 |
|------|--------|
| 格式 | WAV 或 MP3 |
| 时长 | 5-10 秒 |
| 采样率 | 22050Hz 或 32000Hz |
| 声道 | 单声道 (Mono) |
| 内容 | 清晰的完整句子 |

### 3.2 录制建议

1. **安静环境**：避免背景噪音
2. **适中音量**：不要太小或失真
3. **自然语速**：正常说话速度
4. **清晰发音**：避免含糊不清

### 3.3 存放位置

建议统一存放在 GPT-SoVITS 目录下：
```
C:\GPT-SoVITS\voices\
  ├── sherry_reference.wav    # 雪莉默认音色
  ├── angry.wav               # 生气音色
  ├── happy.wav               # 开心音色
  └── ...
```

---

## 4. 测试与故障排除

### 4.1 基础测试

启动后，通过 WebSocket 发送测试消息：

```python
import asyncio
import websockets
import json

async def test():
    uri = "ws://127.0.0.1:8765/sprite"
    async with websockets.connect(uri) as ws:
        # 测试说话
        await ws.send(json.dumps({
            "type": "speak",
            "data": {
                "text": "你好主人，我是雪莉！",
                "provider": "gptsovits"
            }
        }))
        response = await ws.recv()
        print(response)

asyncio.run(test())
```

### 4.2 常见问题

#### 问题 1：连接超时

**现象**：
```
GPT-SoVITS: Request timeout
```

**解决**：
1. 检查 GPT-SoVITS API 是否已启动
2. 检查端口是否占用：`netstat -ano | findstr 9880`
3. 检查防火墙设置

#### 问题 2：参考音频找不到

**现象**：
```
FileNotFoundError: refer_wav_path not found
```

**解决**：
- Windows 路径使用正斜杠：`C:/path/to/audio.wav`
- 或使用双反斜杠：`C:\\path\\to\\audio.wav`
- 确认文件确实存在

#### 问题 3：生成的声音不像

**解决**：
1. 更换更好的参考音频（清晰、无噪音）
2. 调整生成参数：
   ```yaml
   top_k: 10      # 降低多样性
   temperature: 0.5  # 降低随机性
   ```
3. 确保参考音频文本准确

#### 问题 4：语速太快/太慢

**解决**：
```yaml
speed: 0.9   # 慢一点
speed: 1.1   # 快一点
```

#### 问题 5：API 返回错误

查看 GPT-SoVITS 的控制台输出，常见错误：

- **语言不匹配**：`text_language` 与文本实际语言不符
- **模型未加载**：启动 API 时未指定模型路径
- **显存不足**：降低 batch size 或使用 CPU 模式

### 4.3 查看日志

**雪莉日志**：
```powershell
type %USERPROFILE%\.sherry\sprite.log
```

**实时查看**：
```powershell
Get-Content %USERPROFILE%\.sherry\sprite.log -Wait
```

---

## 5. 高级用法

### 5.1 动态切换音色

无需重启雪莉，实时切换不同角色的声音：

```python
await ws.send(json.dumps({
    "type": "gptsovits_config",
    "data": {
        "refer_wav_path": "C:/GPT-SoVITS/voices/angry.wav",
        "prompt_text": "哼！我才不告诉你呢！",
        "prompt_language": "zh"
    }
}))

# 然后说话
await ws.send(json.dumps({
    "type": "speak",
    "data": {"text": "哼！不理你了！"}
}))
```

### 5.2 不同语言支持

#### 中文
```yaml
text_language: "zh"
```

#### 英文
```yaml
text_language: "en"
```

#### 日文
```yaml
text_language: "ja"
```

#### 中英混合
```yaml
text_language: "zh"  # 或 "all_zh" 如果纯中文
```

### 5.3 调整生成质量

| 参数 | 低质量(快) | 平衡 | 高质量(慢) |
|------|-----------|------|-----------|
| top_k | 5 | 20 | 50 |
| top_p | 0.5 | 0.6 | 0.8 |
| temperature | 0.5 | 0.6 | 0.7 |

---

## 6. 一键启动脚本

创建 `start_with_gptsovits.bat`：

```batch
@echo off
chcp 65001

echo [1/2] 启动 GPT-SoVITS API...
cd /d C:\GPT-SoVITS
start "GPT-SoVITS API" python api.py -dr "voices/sherry_reference.wav" -dt "你好，我是雪莉" -dl "zh"

echo 等待 5 秒让 API 启动...
timeout /t 5 /nobreak > nul

echo [2/2] 启动雪莉桌面精灵...
cd /d C:\Users\lianj\Python\desktop-spirit-v2-windows
python start_windows.py

pause
```

双击运行即可同时启动 GPT-SoVITS 和雪莉。

---

**有问题？** 查看日志文件或参考 [GPT-SoVITS 官方文档](https://github.com/RVC-Boss/GPT-SoVITS)
