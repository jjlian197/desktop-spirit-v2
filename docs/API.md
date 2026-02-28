# WebSocket API Documentation

## Connection

```
ws://127.0.0.1:8765/sprite
```

## Message Format

All messages are JSON with the following structure:

```json
{
  "type": "message_type",
  "data": { ... }
}
```

## Commands

### 1. Expression - Change facial expression

```json
{
  "type": "expression",
  "data": {
    "name": "生气"
  }
}
```

**Expression Names:**
Expressions are loaded from the model's `按键/` folder (Chinese models) or `expressions/` folder (standard models).

**Common expressions (Hanamaru model):**
- `生气` - Angry
- `哭哭` - Crying
- `星星眼` - Star eyes (excited)
- `挥手` - Wave hand
- `红脸` - Blushing
- `变Q` - Chibi/Q version
- `呆` - Dazed/blank
- `黑脸` - Dark/black face

**Fuzzy Matching:**
The system supports partial matching:
- `"星"` matches `"星星眼"`
- `"挥"` matches `"挥手"`
- `"哭"` matches `"哭哭"`

**Success Response:**
```json
{
  "type": "expression_set",
  "data": {
    "requested_name": "星",
    "actual_name": "星星眼",
    "available_expressions": ["生气", "哭哭", "星星眼", ...]
  },
  "success": true
}
```

**Error Response:**
```json
{
  "type": "error",
  "data": {
    "message": "Expression 'xyz' not found. Available: [...]"
  },
  "success": false
}
```

See [EXPRESSIONS.md](EXPRESSIONS.md) for the complete expression list.

### 2. Motion - Trigger animation

```json
{
  "type": "motion",
  "data": {
    "group": "tap",
    "index": 0,
    "priority": 2
  }
}
```

**Motion Groups:**
- `idle` - Idle animations
- `tap` - Tap/click response
- `greeting` - Greeting motion

**Priority:**
- `1` - Idle (lowest)
- `2` - Normal
- `3` - Force (highest)

### 3. Message - Show bubble text

```json
{
  "type": "message",
  "data": {
    "text": "Hello Master! 💜",
    "duration": 5000,
    "position": "top"
  }
}
```

### 4. Speak - Text to speech

```json
{
  "type": "speak",
  "data": {
    "text": "Welcome back!",
    "voice": "sherry",
    "lip_sync": true
  }
}
```

### 5. Get Status

```json
{
  "type": "get_status",
  "data": {}
}
```

**Response:**
```json
{
  "type": "status",
  "data": {
    "state": "idle",
    "expression": "生气",
    "position": {"x": 100, "y": 200},
    "connected_clients": 1,
    "available_expressions": ["生气", "哭哭", "星星眼", "挥手", ...],
    "total_expressions": 43
  },
  "success": true
}
```

### 6. Window Control

```json
{
  "type": "window",
  "data": {
    "action": "move",
    "x": 500,
    "y": 300
  }
}
```

**Actions:**
- `move` - Move window (requires `x`, `y`)
- `opacity` - Set opacity (requires `opacity` 0.0-1.0)
- `hide` - Hide window
- `show` - Show window

## Example Python Client

```python
import asyncio
import websockets
import json

async def control_sprite():
    uri = "ws://127.0.0.1:8765/sprite"
    async with websockets.connect(uri) as ws:
        # Get status and available expressions
        await ws.send(json.dumps({
            "type": "get_status",
            "data": {}
        }))
        response = await ws.recv()
        print(f"Available expressions: {response}")
        
        # Send expression (Chinese names for hanamaru model)
        await ws.send(json.dumps({
            "type": "expression",
            "data": {"name": "生气"}  # Angry
        }))
        response = await ws.recv()
        print(f"Expression result: {response}")
        
        # Try fuzzy matching
        await ws.send(json.dumps({
            "type": "expression",
            "data": {"name": "星"}  # Matches "星星眼"
        }))
        response = await ws.recv()
        print(f"Fuzzy match result: {response}")
        
        # Show message
        await ws.send(json.dumps({
            "type": "message",
            "data": {"text": "Meow~ Master! 💜", "duration": 3000}
        }))
        response = await ws.recv()
        print(f"Message result: {response}")

asyncio.run(control_sprite())
```
