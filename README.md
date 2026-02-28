# Sherry Desktop Sprite 🐱💜

> A cute desktop pet powered by Live2D and PyQt6 for macOS

![Python](https://img.shields.io/badge/python-3.9+-blue.svg)
![Platform](https://img.shields.io/badge/platform-macos-lightgrey.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

## ✨ Features

- 🎭 **Live2D Support** - Smooth 2D character animation with physics and expressions
- 😊 **Expression Control** - 43+ facial expressions and poses via WebSocket API
- 🪟 **Transparent Window** - Frameless, always-on-top display
- 🔌 **WebSocket API** - Remote control for expression, motion, and messages
- 💬 **Bubble Messages** - Floating speech bubbles
- 🔊 **TTS Integration** - Text-to-speech using macOS `say` command
- 🔄 **Auto-Restart** - launchd integration for 24/7 uptime
- 🖱️ **Draggable** - Click and drag to move anywhere

## 🚀 Quick Start

### Prerequisites

- macOS 11+ (Apple Silicon or Intel)
- Python 3.9+

### Installation

```bash
# Clone or navigate to project
cd /Users/mylianjie/.openclaw/workspace/projects/sherry-desktop-sprite

# Install dependencies
pip3 install -r requirements.txt

# Run the sprite
python3 src/main.py
```

### Install as Service (Auto-start)

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

See [docs/API.md](docs/API.md) for full API documentation and [docs/EXPRESSIONS.md](docs/EXPRESSIONS.md) for expression reference.

## 📁 Project Structure

```
sherry-desktop-sprite/
├── src/
│   ├── main.py                 # Entry point
│   ├── app.py                  # Main application
│   ├── core/
│   │   ├── sprite_window.py    # PyQt6 transparent window
│   │   ├── live2d_view.py      # Live2D renderer
│   │   └── websocket_server.py # WebSocket control
│   ├── ui/
│   │   └── bubble_widget.py    # Message bubbles
│   └── utils/
│       └── logger.py           # Logging setup
├── launchd/
│   └── com.sherry.sprite.plist # macOS service config
├── scripts/
│   ├── install.sh              # One-click installer
│   └── uninstall.sh            # Uninstall script
├── tests/
│   └── test_client.py          # WebSocket test client
├── docs/
│   ├── API.md                  # API documentation
│   ├── DEPLOY.md               # Deployment guide
│   └── MODELS.md               # Live2D model setup
├── requirements.txt
└── config.yaml
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
