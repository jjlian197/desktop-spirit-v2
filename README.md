# Sherry Desktop Sprite

> A cute desktop pet powered by Live2D / VRM and PyQt6 (Windows & macOS)

![Python](https://img.shields.io/badge/python-3.9+-blue.svg)
![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS-lightgrey.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

## Features

- **Dual Renderer** - Live2D (2D) and VRM/GLB (3D) character rendering, switchable via right-click menu
- **Live2D Support** - Smooth 2D animation with physics, expressions, and motion files
- **VRM/GLB Support** - 3D character models from Blender with bone-based gestures (wave, shy, nod, shake, think, stretch)
- **Expression Control** - 43+ facial expressions for Live2D; expression mapping for VRM models
- **Procedural Animations** - Idle breathing/sway, eye tracking, lip sync for both renderers
- **Transparent Window** - Frameless, always-on-top display with draggable interaction
- **Dynamic Background** - Change background color/image/gradient via API
- **WebSocket & HTTP API** - Remote control for all features
- **Bubble Messages** - Floating speech bubbles
- **TTS Integration** - Text-to-speech with Edge-TTS, GPT-SoVITS, and multi-language support
- **AI Translation** - Support OpenAI/Baidu/Youdao/Niutrans for quality translation
- **Blender Pipeline** - Export script (`tools/export_blend_to_glb.py`) for simplified material export

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

## Project Structure

```
sherry-desktop-sprite/
├── src/                        # Main source code
│   ├── main.py                 # Entry point
│   ├── core/                   # Core modules
│   │   ├── sprite_window.py    # PyQt6 transparent window, renderer management
│   │   ├── live2d_view.py      # Live2D renderer
│   │   ├── vrm_view.py         # VRM/GLB renderer (Three.js via QWebEngine)
│   │   ├── websocket_server.py # WebSocket control
│   │   ├── tts_manager.py      # Text-to-speech
│   │   └── lip_sync_websocket.py # Lip sync
│   ├── brain/                  # AI & Intelligence
│   │   └── sprite_brain.py     # Autonomous behavior, idle system
│   ├── ui/                     # UI components
│   │   └── bubble_widget.py    # Message bubbles
│   └── assets/
│       ├── models/
│       │   ├── hanamaru/       # Default Live2D model
│       │   └── vrm/            # VRM/GLB models
│       └── vrm_viewer/         # Three.js viewer (viewer.js, index.html)
├── tools/                      # Development tools
│   ├── export_blend_to_glb.py  # Blender export script (GLB/VRM)
│   └── ...
├── docs/                       # Documentation
├── config.yaml                 # Main configuration
└── requirements.txt            # Python dependencies
```

## Models

### Live2D

Place Live2D models in `src/assets/models/`:

```bash
src/assets/models/hanamaru/
├── hiyori.model3.json
├── textures/
├── motions/
└── expressions/
```

### VRM / GLB (3D)

Place VRM/GLB models in `src/assets/models/vrm/`. Export from Blender using:

```bash
blender -b your_model.blend -P tools/export_blend_to_glb.py -- output.glb
```

Switch renderers via the right-click menu or `config.yaml`:

```yaml
sprite:
  renderer: vrm   # or live2d
  vrm:
    path: src/assets/models/vrm/your-model.glb
```

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

## Roadmap

- [x] Basic PyQt6 window with transparency
- [x] WebSocket control API
- [x] Message bubbles
- [x] Live2D model integration
- [x] Expression control (43+ expressions)
- [x] Voice synthesis with lip sync
- [x] Idle animations
- [x] Interactive responses
- [x] Windows support
- [x] VRM/GLB 3D model renderer (Three.js + QWebEngine)
- [x] Blender export pipeline with material simplification
- [x] Bone-based procedural gestures for 3D models
- [ ] Settings UI
- [ ] Increase gesture amplitude for 3D models

## 📄 License

MIT License - See LICENSE file for details.

## 💜 Credits

Made with love for Lian's Mac mini 🐱💜

Live2D models are subject to their respective licenses.

---

> "Master, Sherry will always be here for you meow~ 💜"
