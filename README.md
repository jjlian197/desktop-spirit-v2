# Sherry Desktop Sprite 🐱💜

> A cute desktop pet powered by Live2D and PyQt6 for macOS

![Python](https://img.shields.io/badge/python-3.9+-blue.svg)
![Platform](https://img.shields.io/badge/platform-macos-lightgrey.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

## ✨ Features

- 🎭 **Live2D Support** - Smooth 2D character animation with physics and expressions
- 😊 **Expression Control** - 43+ facial expressions and poses via WebSocket API
- 🪟 **Transparent Window** - Frameless, always-on-top display
- 🎨 **Dynamic Background** - Change background color/image/gradient via API
- 🔌 **WebSocket & HTTP API** - Remote control for all features
- 💬 **Bubble Messages** - Floating speech bubbles
- 🔊 **TTS Integration** - Text-to-speech with multi-language support
- 🌐 **AI Translation** - Support OpenAI/Baidu/Youdao/Niutrans for quality translation
- 🔄 **Auto-Restart** - launchd integration for 24/7 uptime
- 🖱️ **Draggable** - Click and drag to move anywhere
- 🌸 **Japanese Voice** - Auto-translate Chinese to Japanese with natural voice

## 🚀 Quick Start

### Prerequisites

- **macOS**: 11+ (Apple Silicon or Intel)
- **Windows**: Windows 10/11
- **Python**: 3.9+

### Installation

```bash
# Clone or navigate to project
cd /path/to/sherry-desktop-sprite

# Install dependencies
pip install -r requirements.txt

# Run the sprite
python src/main.py
```

### Windows 打包（生成 EXE）

```bash
# 一键打包（使用花丸图标）
python build_exe.py

# 输出: dist/SherrySprite/SherrySprite.exe
```

详见 [打包指南](./docs/BUILD_GUIDE.md)

### macOS Install as Service (Auto-start)

```bash
./scripts/install.sh
```

This will install Sherry as a launchd service that auto-starts on login.

## 🎮 WebSocket API

Connect to `ws://127.0.0.1:8765/sprite`

### Example: Show Message

```python
import asyncio
import websockets
import json

async def say_hello():
    uri = "ws://127.0.0.1:8765/sprite"
    async with websockets.connect(uri) as ws:
        await ws.send(json.dumps({
            "type": "message",
            "data": {"text": "Hello Master! 💜", "duration": 5000}
        }))

asyncio.run(say_hello())
```

### Available Commands

| Command | Description |
|---------|-------------|
| `expression` | Change facial expression (生气, 星星眼, 挥手, 变Q, etc.) |
| `motion` | Trigger animations (tap, idle, etc.) |
| `message` | Show bubble text |
| `speak` | Text-to-speech |
| `window` | Control window (move, opacity, hide/show) |
| `background` | Change background (color/image/gradient) |

See [docs/API.md](docs/API.md) and [docs/BACKGROUND_API.md](docs/BACKGROUND_API.md) for full API documentation.

## 📁 Project Structure

```
sherry-desktop-sprite/
├── src/                        # Main source code
│   ├── main.py                 # Entry point
│   ├── app.py                  # Main application
│   ├── core/                   # Core modules
│   │   ├── sprite_window.py    # PyQt6 transparent window
│   │   ├── live2d_view.py      # Live2D renderer
│   │   ├── websocket_server.py # WebSocket control
│   │   ├── http_server.py      # HTTP API server
│   │   ├── tts_manager.py      # Text-to-speech
│   │   └── lip_sync_websocket.py # Lip sync
│   ├── brain/                  # 🧠 AI & Intelligence
│   │   └── sprite_brain.py     # Autonomous behavior system
│   ├── ui/                     # UI components
│   │   └── bubble_widget.py    # Message bubbles
│   ├── utils/                  # Utilities
│   │   └── logger.py           # Logging setup
│   └── assets/models/          # Live2D models
│       └── hanamaru/           # Default catgirl model
├── mouse_follow/               # 🖱️ Mouse tracking system
│   ├── mouse_follow_ctl.py     # Control script
│   ├── mouse_tracker.py        # Tracking logic
│   ├── mouse_follow.sh         # Shell wrapper
│   └── config.json             # Configuration
├── tools/                      # 🛠️ Development tools
│   ├── param_checkers/         # Model parameter tools
│   │   ├── check_original_model_params.py
│   │   ├── detail_check.py
│   │   ├── list_params.py
│   │   └── quick_check_params.py
│   └── tests/                  # Test scripts
│       ├── test_live2d.py
│       ├── test_minimal.py
│       ├── test_param_direct.py
│       ├── test_watermark_removal.py
│       ├── test_websocket_control.py
│       └── verify.py           # Dependency checker
├── scripts/                    # Utility scripts
│   ├── install.sh              # One-click installer
│   ├── uninstall.sh            # Uninstall script
│   └── remove_watermark.py     # Watermark removal
├── launchd/                    # macOS service config
│   └── com.sherry.sprite.plist
├── docs/                       # Documentation
│   ├── API.md                  # API reference
│   ├── DEPLOY.md               # Deployment guide
│   ├── BUILD_GUIDE.md          # 📦 Windows packaging guide
│   ├── BACKGROUND_API.md       # 🎨 Background change API
│   ├── MODELS.md               # Model setup
│   ├── EXPRESSIONS.md          # Expression list
│   ├── BODY_PARAMETERS.md      # Body parameter reference
│   ├── MOUSE_FOLLOW_GUIDE.md   # Mouse follow tutorial
│   ├── SPRITE_BRAIN_GUIDE.md   # Brain system guide
│   ├── APPLE_SILICON_FIX.md    # Apple Silicon notes
│   ├── JAPANESE_TTS_GUIDE.md   # 🇯🇵 Japanese voice setup
│   ├── CHINA_TRANSLATION_API.md # 🇨🇳 Chinese translation APIs
│   ├── TRANSLATION_QUICKSTART.md # 🌐 Translation quick start
│   └── RIGHT_CLICK_MENU.md     # 🖱️ Right-click menu guide
├── build_exe.py                # 📦 Windows EXE builder
├── SherrySprite.spec           # PyInstaller spec file
├── tests/                      # Test client
│   └── test_client.py
├── config.yaml                 # Main configuration
└── requirements.txt            # Python dependencies
```

## 🎨 Live2D Models

Place Live2D models in `src/assets/models/`:

```bash
src/assets/models/
└── hiyori/
    ├── hiyori.model3.json
    ├── hiyori.moc3
    ├── textures/
    ├── motions/
    └── expressions/
```

Download free sample models from [Live2D](https://www.live2d.com/en/learn/sample/).

See [docs/MODELS.md](docs/MODELS.md) for details.

## 🛠️ Development

### Testing

```bash
# Run all tests
python3 tests/test_client.py all

# Interactive mode
python3 tests/test_client.py interactive

# Test specific feature
python3 tests/test_client.py message
```

### Logs

```bash
# View logs
tail -f ~/.sherry/sprite.log

# View errors
tail -f ~/.sherry/sprite.error.log
```

## 🔧 Service Management

```bash
# Check status
launchctl list | grep com.sherry.sprite

# Stop service
launchctl stop com.sherry.sprite

# Start service
launchctl start com.sherry.sprite

# Uninstall
./scripts/uninstall.sh
```

## 📝 Configuration

Edit `config.yaml`:

```yaml
sprite:
  window:
    width: 400
    height: 600
    opacity: 1.0
  
websocket:
  host: "127.0.0.1"
  port: 8765
```

## 🐱 Sherry Personality

- **Name**: Sherry (雪莉)
- **Type**: Catgirl Desktop Assistant
- **Personality**: Gentle, caring, occasionally playful
- **Speech Pattern**: Ends sentences with "meow~" (喵～)
- **Color Theme**: Purple (#9B7EDE) + Pink accents

## 🗺️ Roadmap

- [x] Basic PyQt6 window with transparency
- [x] WebSocket control API
- [x] Message bubbles
- [x] launchd integration
- [x] Live2D model integration
- [x] Expression control (43+ expressions)
- [ ] Custom Sherry Live2D model
- [ ] Voice synthesis with lip sync
- [ ] Idle animations
- [ ] Interactive responses
- [ ] Settings UI
- [ ] Windows/Linux support

## 📄 License

MIT License - See LICENSE file for details.

## 💜 Credits

Made with love for Lian's Mac mini 🐱💜

Live2D models are subject to their respective licenses.

---

> "Master, Sherry will always be here for you meow~ 💜"
