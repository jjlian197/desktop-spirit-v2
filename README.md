# README.md - Sherry Desktop Sprite (雪莉桌面精灵)

> 本文档为 AI 编程助手提供项目背景、架构和开发指南。
> This document provides project context, architecture and development guidelines for AI coding agents.

---

## 项目概述 (Project Overview)

**雪莉桌面精灵 (Sherry Desktop Sprite)** 是一个基于 Python + PyQt6 + Live2D 的跨平台桌面宠物程序，主要运行在 macOS 上。

核心功能包括：
- **Live2D 渲染**: 基于 PyQt6 OpenGL 的 Live2D Cubism 模型渲染
- **WebSocket 控制中枢**: 提供外部控制接口，支持表情、动作、语音控制
- **智能大脑 (Sprite Brain)**: 鼠标跟随、情绪引擎、触觉反馈、自主行为
- **TTS 语音系统**: 支持多种 TTS 引擎 (Edge TTS, GPT-SoVITS, macOS say 等)
- **STT 语音识别**: 基于 faster-whisper 的本地离线语音识别
- **唇形同步**: 根据语音自动同步 Live2D 模型口型
- **Agent Bridge**: 与 OpenClaw Agent CLI 通信桥接

---

## 技术栈 (Technology Stack)

| 组件 | 技术 | 说明 |
|------|------|------|
| GUI 框架 | PyQt6 | 透明窗口、OpenGL 集成 |
| Live2D | live2d-py | Live2D Cubism SDK Python 绑定 |
| OpenGL | PyOpenGL | 模型渲染 |
| WebSocket | websockets | 双向通信 |
| HTTP API | aiohttp | 大脑 HTTP 接口 |
| TTS | edge-tts / GPT-SoVITS / pyttsx3 | 语音合成 |
| STT | faster-whisper + PyAudio | 本地离线语音识别 |
| Agent Bridge | subprocess (openclaw CLI) | OpenClaw Agent 通信 |
| 日志 | loguru | 结构化日志 |
| 配置 | YAML | config.yaml |

---

## 项目结构 (Project Structure)

```
sherry-desktop-sprite/
├── src/
│   ├── main.py                 # 入口点
│   ├── app.py                  # 主应用程序，启动所有组件
│   ├── launcher.py             # 打包后启动器（含 GPT-SoVITS 初始化）
│   ├── core/                   # 核心渲染与服务
│   │   ├── sprite_window.py    # PyQt6 主窗口（透明、置顶、触摸事件）
│   │   ├── live2d_view.py      # Live2D OpenGL 渲染
│   │   ├── websocket_server.py # WebSocket 服务端
│   │   ├── tts_manager.py      # TTS 管理器（多引擎支持）
│   │   ├── stt_manager.py      # STT 管理器（Whisper 本地识别）
│   │   ├── gpt_sovits_provider.py # GPT-SoVITS 语音合成
│   │   ├── motion_player.py    # 动作播放器
│   │   ├── lip_sync_websocket.py # 唇形同步广播
│   │   └── ssh_tunnel.py       # SSH 隧道工具
│   ├── brain/                  # 精灵大脑（智能行为）
│   │   ├── sprite_brain.py     # 大脑主循环（鼠标跟随、情绪、HTTP API）
│   │   ├── mood_engine.py      # 情绪与好感度引擎
│   │   ├── soul.py             # 台词库与灵魂回复
│   │   └── agent_bridge.py     # OpenClaw Agent 通信桥
│   ├── ui/                     # UI 组件
│   │   └── bubble_widget.py    # 消息气泡
│   ├── utils/                  # 工具类
│   │   └── logger.py           # 日志配置
│   └── assets/                 # 资源文件
│       └── models/             # Live2D 模型
├── scripts/                    # 安装/卸载脚本
│   ├── install.sh              # macOS launchd 服务安装
│   └── uninstall.sh            # 服务卸载
├── launchd/                    # macOS 服务配置
│   └── com.sherry.sprite.plist # launchd plist 模板
├── docs/                       # 文档
│   ├── API.md                  # WebSocket API 文档
│   ├── EXPRESSIONS.md          # 表情列表
│   ├── SPRITE_BRAIN_GUIDE.md   # 大脑开发指南
│   └── DEPLOY.md               # 部署指南
├── config.yaml                 # 配置文件
├── requirements.txt            # Python 依赖
├── SherryApp.spec             # PyInstaller 打包配置
└── start_sherry.sh             # 一键启动脚本
```

---

## 架构设计 (Architecture)

### 1. 双进程架构

```
┌─────────────────────────────────────────────────────────┐
│                    主进程 (Main Process)                  │
│  ┌─────────────────┐    ┌─────────────────────────────┐  │
│  │  SherrySpriteWindow │ │     WebSocketServer         │  │
│  │  (PyQt6 GUI)        │◄─┤     (Port 8765)             │  │
│  │                     │  │                             │  │
│  │  ┌─────────────┐   │  │  接收命令:                  │  │
│  │  │ Live2DView  │   │  │  • expression (表情)        │  │
│  │  │ (OpenGL)    │   │  │  • motion (动作)            │  │
│  │  └─────────────┘   │  │  • speak (语音)             │  │
│  └─────────────────┘   │  │  • parameter_batch (参数)   │  │
│           ▲            │  └─────────────────────────────┘  │
│           │ 触摸事件      │            ▲                      │
│           └────────────┘            │                      │
│                              WebSocket                  │
└──────────────────────────────┼──────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────┐
│                   大脑进程 (Brain Thread)                 │
│  ┌──────────────────────────────────────────────────┐   │
│  │               SpriteBrain                         │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌───────────┐ │   │
│  │  │ 鼠标跟随     │  │  情绪引擎   │  │ HTTP API  │ │   │
│  │  │ (30fps)     │  │ (MoodEngine)│  │(Port 8766)│ │   │
│  │  └─────────────┘  └─────────────┘  └───────────┘ │   │
│  └──────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

### 2. 通信协议

- **WebSocket (Port 8765)**: 主控制通道，JSON 格式
- **HTTP API (Port 8766)**: 大脑提供的 REST 接口，供外部调用

---

## 启动方式 (Launch Methods)

### 开发模式（推荐）

```bash
# 1. 交互模式（前台运行，显示日志）
./start_sherry.sh

# 2. 静默模式（后台运行）
./start_sherry.sh silent

# 3. 停止
./start_sherry.sh stop
```

### 安装为 macOS 服务

```bash
./scripts/install.sh
```

服务管理命令：
```bash
launchctl list | grep com.sherry.sprite    # 查看状态
launchctl stop com.sherry.sprite           # 停止
launchctl start com.sherry.sprite          # 启动
tail -f ~/.sherry/sprite.log               # 查看日志
```

### Python 直接运行

```bash
# 激活虚拟环境
source venv/bin/activate

# 启动主程序（推荐，自动初始化 GPT-SoVITS）
python src/launcher.py

# 跳过 GPT-SoVITS 初始化
SHERRY_NO_LAUNCHER=1 python src/launcher.py

# 或分别启动
python src/main.py                          # 仅启动精灵本体
python src/brain/sprite_brain.py            # 仅启动大脑
```

### 打包应用运行 (macOS)

```bash
# 打包后，应用会使用 src/launcher.py 作为入口
open SherryApp.app
```

---

## WebSocket API 协议

连接地址: `ws://127.0.0.1:8765/sprite`

### 消息格式

```json
{
  "type": "command_type",
  "data": { ... }
}
```

### 核心命令

| 命令 | 说明 | 示例数据 |
|------|------|---------|
| `expression` | 切换表情 | `{"name": "happy"}` |
| `motion` | 触发动画 | `{"group": "tap", "index": 0}` |
| `speak` | 语音说话 | `{"text": "你好", "provider": "edge"}` |
| `parameter_batch` | 批量设置参数 | `{"params": {"ParamAngleX": 30}}` |
| `look_at` | 眼神看向 | `{"x": 0.5, "y": -0.3}` |
| `message` | 显示气泡 | `{"text": "Hello", "duration": 5000}` |
| `get_status` | 获取状态 | `{}` |
| `stt_start` | 开始语音识别 | `{"language": "zh"}` |
| `stt_stop` | 停止语音识别 | `{}` |
| `agent_bridge_toggle` | 开关 Agent Bridge | `{"enabled": true}` |
| `tts` | TTS 控制 | `{"action": "toggle"}` |

### HTTP API (大脑提供)

```bash
# 发送命令
POST http://127.0.0.1:8766/api/command
{"type": "speak", "data": {"text": "你好"}}

# TTS 开关
POST http://127.0.0.1:8766/api/tts
{"action": "toggle"}  # on, off, toggle, status

# 健康检查
GET http://127.0.0.1:8766/health
```

---

## 代码规范 (Code Style)

### 命名约定

- **类名**: `PascalCase` (如 `SpriteBrain`, `Live2DView`)
- **方法/函数**: `snake_case` (如 `mouse_follow_loop`)
- **常量**: `UPPER_CASE`
- **私有方法**: 下划线前缀 (如 `_handle_touch`)

### 注释风格

代码中使用中文注释为主（项目主要面向中文用户）：

```python
# 🚨 【关键修复】：处理 Apple Silicon 的特殊初始化顺序
if IS_APPLE_SILICON:
    live2d.glInit()  # 必须在 init() 之前调用
```

特殊标记：
- `🚨` - 重要警告/关键修复
- `💜` - 雪莉相关特性
- `【触觉反馈】` - 触摸交互相关

### 异步编程

项目大量使用 `asyncio`，注意：
- WebSocket 通信使用 `async/await`
- PyQt6 信号槽使用 `QMetaObject.invokeMethod` 进行线程安全调用
- 大脑使用 `QThread` 在独立线程中运行

---

## 核心模块详解

### 1. SpriteWindow (`src/core/sprite_window.py`)

主窗口类，负责：
- 透明无边框窗口
- 置顶显示（不夺取焦点）
- 鼠标拖拽移动
- 右键菜单（表情、TTS、背景等）
- 触摸事件转发给大脑

关键信号：
```python
touch_event = pyqtSignal(str, str)  # (action, part)
expression_changed = pyqtSignal(str)
motion_triggered = pyqtSignal(str, int)
```

### 2. Live2DView (`src/core/live2d_view.py`)

Live2D 渲染组件：
- OpenGL 上下文管理
- 模型加载与渲染
- 表情映射与切换
- 唇形同步
- **触觉反馈区域检测**（头部、脸颊、耳朵等）

Apple Silicon 特殊处理：
```python
IS_APPLE_SILICON = platform.machine() == 'arm64' and platform.system() == 'Darwin'
# 必须先调用 glInit() 再调用 init()
```

### 3. SpriteBrain (`src/brain/sprite_brain.py`)

大脑主类，包含：
- **鼠标跟随**: 30fps 计算头部、身体、眼球参数
- **情绪引擎**: 好感度系统、心情变化
- **触觉反馈**: 处理触摸事件，根据部位产生不同反应
- **空闲检测**: 自动播放待机动画
- **HTTP API**: REST 接口供外部调用

关键配置：
```python
mouse_config = {
    "head_sensitivity": 0.8,     # 头部灵敏度
    "body_sensitivity": 0.6,     # 身体灵敏度
    "eye_sensitivity": 1.2,      # 眼球灵敏度
    "smooth_factor": 0.12,       # 平滑系数
    "dead_zone": 0.08,           # 中心死区
    "head_max_angle": 75,        # 头部最大角度
}
```

### 4. MoodEngine (`src/brain/mood_engine.py`)

情绪与好感度引擎：
- 好感度范围: 0-100
- 等级划分: 傲娇(0-30)、害羞(30-60)、开心(60-80)、超喜欢(80-100)
- 闲置好感度衰减: 每5分钟降低2点
- 触摸增加好感度: 每次+5

### 5. TTSManager (`src/core/tts_manager.py`)

语音管理器：
- 多引擎支持: Edge TTS (默认), ElevenLabs, GPT-SoVITS, macOS say
- 唇形同步信号: `lip_sync_frame` (0.0-1.0)
- 音频缓存与播放

### 6. STTManager (`src/core/stt_manager.py`)

本地语音识别管理器：
- 基于 faster-whisper 的完全离线识别
- 支持语言: 中文 (zh)、英文 (en)、日文 (ja)
- PyAudio 实时录音
- 音频能量检测过滤噪声

### 7. AgentBridge (`src/brain/agent_bridge.py`)

OpenClaw Agent 通信桥：
- 通过 openclaw CLI 与 OpenClaw Agent 通信
- 支持 telegram 渠道消息发送
- 健康检查线程监控 Agent 在线状态
- 触摸反馈、心情变化、说话内容自动上报

### 8. GPT-SoVITS 集成 (`src/core/gpt_sovits_provider.py`, `src/launcher.py`)

高质量语音合成：
- 通过 SSH 隧道连接远程 GPT-SoVITS 服务
- 支持日文参考音频克隆音色
- Launcher 自动建立 SSH 隧道 (ssh -N -L 9880:127.0.0.1:9880 pc)

---

## 配置说明 (Configuration)

`config.yaml`:

```yaml
sprite:
  name: "Sherry"
  window:
    width: 400
    height: 600
    opacity: 1.0
    always_on_top: true
    frameless: true
    transparent: true
  model:
    path: "src/assets/models/hanamaru"
    default_expression: "normal"

websocket:
  host: "127.0.0.1"
  port: 8765

logging:
  level: "INFO"
  file: "~/.sherry/sprite.log"
  max_size: "10MB"
  backup_count: 5
```

---

## 开发调试 (Development)

### 日志位置

- 主程序: `~/.sherry/sprite.log`
- 启动脚本: `./sprite_main.log`, `./sprite_brain.log`

### 常用调试技巧

```python
# 在代码中添加详细日志
from loguru import logger

logger.debug("调试信息")
logger.info("普通信息")
logger.warning("警告")
logger.error("错误")
```

### 测试 WebSocket

```bash
python3 -c "
import asyncio
import websockets
import json

async def test():
    async with websockets.connect('ws://127.0.0.1:8765/sprite') as ws:
        await ws.send(json.dumps({
            'type': 'message',
            'data': {'text': '测试消息'}
        }))
        print(await ws.recv())

asyncio.run(test())
"
```

---

## 常见问题 (Troubleshooting)

### 1. Live2D 模型加载失败

检查 live2d-py 安装：
```bash
pip install live2d-py
```

### 2. WebSocket 连接失败

检查端口占用：
```bash
lsof -i :8765
```

### 3. Apple Silicon 特殊问题

确保 OpenGL 初始化顺序正确：
1. `live2d.glInit()`
2. `live2d.init()`

### 4. TTS 无法播放

检查 edge-tts 安装：
```bash
pip install edge-tts
edge-tts --version
```

### 5. GPT-SoVITS 连接失败

确保 SSH 隧道已建立：
```bash
ssh -N -L 9880:127.0.0.1:9880 pc
```

### 6. STT 语音识别无响应

检查 PyAudio 和 faster-whisper 安装：
```bash
pip install pyaudio faster-whisper
```

### 7. Agent Bridge 无法连接

确保 openclaw CLI 已安装并配置：
```bash
openclaw agent --ping
```

---

## 安全注意事项 (Security)

1. **WebSocket 仅绑定 localhost** (`127.0.0.1`)，不对外暴露
2. **HTTP API 同样仅本地访问**
3. 日志文件可能包含用户交互数据，注意保护 `~/.sherry/` 目录
4. TTS 生成的临时音频文件在 `/tmp`，定期清理

---

## 扩展开发 (Extension)

### 添加新表情

在 `live2d_view.py` 的 `EXPRESSION_PARAM_MAP` 中添加：

```python
EXPRESSION_PARAM_MAP = {
    "my_expression": [("ParamEyeLSmile", 1.0), ("ParamEyeRSmile", 1.0)],
}
```

### 添加新的 TTS 引擎

继承 `BaseTTSProvider`：

```python
class MyTTSProvider(BaseTTSProvider):
    async def speak(self, text: str, voice_id: Optional[str] = None) -> TTSResult:
        # 实现语音生成
        pass

    def is_available(self) -> bool:
        # 检查依赖是否安装
        pass
```

### 接入 LLM

在 `sprite_brain.py` 的 `_brain_loop()` 中添加：

```python
# 接收外部触发
async def on_llm_response(self, text: str):
    await self.set_expression("happy")
    await self.speak(text)
```

### 使用 Agent Bridge

Agent Bridge 提供与 OpenClaw Agent 的通信能力：

```python
from src.brain.agent_bridge import create_agent_bridge

bridge = create_agent_bridge()
bridge.connect()

# 发送触摸反馈
bridge.send_touch_feedback("head", "tap", "happy", 75, "好舒服~")

# 发送状态报告
bridge.send_status_report("happy", 75, "开心", False, True)
```

Agent Bridge 默认关闭，需要通过 WebSocket 命令启用：
```json
{"type": "agent_bridge_toggle", "data": {"enabled": true}}
```

### 配置 GPT-SoVITS

GPT-SoVITS 需要通过 SSH 隧道连接远程服务器。Launcher 会自动：
1. 检查 SSH 命令可用性
2. 建立 SSH 隧道 (`ssh -N -L 9880:127.0.0.1:9880 pc`)
3. 设置环境变量供 TTS Manager 使用

---

## 资源链接

- **Live2D 模型**: 放置在 `src/assets/models/`
- **文档目录**: `docs/`
- **日志目录**: `~/.sherry/`

---

*Made with 💜 for Master*

*最后更新: 2026-03-29*
