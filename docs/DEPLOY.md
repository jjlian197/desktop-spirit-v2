# Deployment Guide

## Quick Start

### 1. Install Dependencies

```bash
cd /Users/mylianjie/.openclaw/workspace/projects/sherry-desktop-sprite
pip3 install -r requirements.txt
```

### 2. Run Directly

```bash
python3 src/main.py
```

### 3. Install as Service (macOS)

```bash
./scripts/install.sh
```

This will:
- Install Python dependencies
- Create launchd plist
- Start Sherry as a background service

## Service Management

### Check Status
```bash
launchctl list | grep com.sherry.sprite
```

### View Logs
```bash
tail -f ~/.sherry/sprite.log
tail -f ~/.sherry/sprite.error.log
```

### Stop Service
```bash
launchctl stop com.sherry.sprite
```

### Start Service
```bash
launchctl start com.sherry.sprite
```

### Uninstall
```bash
./scripts/uninstall.sh
```

## Configuration

Edit `config.yaml` to customize:

```yaml
sprite:
  window:
    width: 400
    height: 600
    opacity: 1.0
    always_on_top: true
  
websocket:
  host: "127.0.0.1"
  port: 8765
```

## Live2D Models

Place Live2D models in:
```
src/assets/models/
```

Model structure:
```
model_name/
├── model_name.model3.json
├── model_name.moc3
├── textures/
├── motions/
└── expressions/
```

Update `config.yaml`:
```yaml
model:
  path: "src/assets/models/model_name"
```

## Troubleshooting

### Port already in use
Change the port in `config.yaml`:
```yaml
websocket:
  port: 8766
```

### Live2D not loading
Ensure `live2d-py` is installed:
```bash
pip3 install live2d-py
```

### Window not transparent (macOS)
This is a known limitation. The window uses transparency but macOS may show a shadow.

## Testing

Test WebSocket connection:
```bash
python3 -c "
import asyncio
import websockets
import json

async def test():
    async with websockets.connect('ws://127.0.0.1:8765/sprite') as ws:
        await ws.send(json.dumps({
            'type': 'message',
            'data': {'text': 'Hello from test!'}
        }))
        print(await ws.recv())

asyncio.run(test())
"
```
