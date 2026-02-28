# Expression Control API

## Overview

Sherry Desktop Sprite supports expression control through WebSocket commands. Expressions are loaded from the model's `按键` (expressions) folder.

## WebSocket Command

```json
{
  "type": "expression",
  "data": {
    "name": "生气"
  }
}
```

## Available Expressions (Hanamaru Model)

The hanamaru model includes 43 expressions in the `按键` folder:

### Facial Expressions
| Name | Description |
|------|-------------|
| `生气` | Angry |
| `哭哭` | Crying |
| `呆` | Dazed/Blank |
| `红脸` | Blushing |
| `黑脸` | Black face/Dark |
| `星星眼` | Star eyes (Excited) |
| `哈气` | Hiss/Yawn |
| `剪刀眼` | Scissor eyes |

### Actions & Poses
| Name | Description |
|------|-------------|
| `挥手` | Wave hand |
| `比心` | Heart hands |
| `猫爪` | Cat paw gesture |
| `飞头` | Flying head |
| `手机` | Holding phone |
| `话筒` | Holding microphone |
| `端酒` | Holding wine glass |

### Props & Accessories
| Name | Description |
|------|-------------|
| `叼猫条` | Cat treat in mouth |
| `叼内裤` | Underwear in mouth |
| `垃圾袋` | Garbage bag |
| `眼罩` | Eyepatch |
| `摸脸` | Touching face |
| `捏脸` | Pinching face |

### Toggles & Variations
| Name | Description |
|------|-------------|
| `变Q` | Chibi/Q version |
| `前发` | Front hair toggle |
| `后发` | Back hair toggle |
| `鬓发` | Side hair toggle |
| `尾巴显示隐藏` | Tail visibility |
| `头顶小猫显隐` | Small cat on head |
| `左头饰显示隐藏` | Left accessory |
| `右头饰显示隐藏` | Right accessory |
| `左耳环显示隐藏` | Left earring |
| `右耳环显示隐藏` | Right earring |
| `腰间大蝴蝶结` | Large waist bow |
| `腰间小蝴蝶结` | Small waist bow |
| `腰间花朵装饰` | Waist flower |

### Color Changes
| Name | Description |
|------|-------------|
| `头发换色` | Hair color |
| `头发自定义改色` | Custom hair color |
| `眼睛换色` | Eye color |
| `猫耳换色` | Cat ear color |
| `衣服换色` | Outfit color |

### Other
| Name | Description |
|------|-------------|
| `去水印` | Remove watermark |
| `LOOK眼镜` | Glasses |
| `抬脚开关` | Foot lift |

## Fuzzy Matching

The expression system supports fuzzy matching:

- `"星"` matches `"星星眼"`
- `"挥"` matches `"挥手"`
- `"哭"` matches `"哭哭"`

## Example Python Client

```python
import asyncio
import websockets
import json

async def set_expression(name):
    uri = "ws://127.0.0.1:8765/sprite"
    async with websockets.connect(uri) as ws:
        await ws.send(json.dumps({
            "type": "expression",
            "data": {"name": name}
        }))
        response = await ws.recv()
        data = json.loads(response)
        
        if data.get("success"):
            actual = data["data"]["actual_name"]
            print(f"✅ Expression set: {name} -> {actual}")
        else:
            print(f"❌ Error: {data['data']['message']}")

# Test expressions
asyncio.run(set_expression("生气"))     # Angry
asyncio.run(set_expression("星星眼"))   # Star eyes
asyncio.run(set_expression("挥手"))     # Wave
```

## Response Format

**Success:**
```json
{
  "type": "expression_set",
  "data": {
    "requested_name": "星",
    "actual_name": "星星眼",
    "available_expressions": [...]
  },
  "success": true
}
```

**Error (expression not found):**
```json
{
  "type": "error",
  "data": {
    "message": "Expression 'xyz' not found. Available: [...]"
  },
  "success": false
}
```

## Getting Available Expressions

To get the list of available expressions:

```python
await ws.send(json.dumps({
    "type": "get_status",
    "data": {}
}))
response = await ws.recv()
data = json.loads(response)
expressions = data["data"]["available_expressions"]
```

## Implementation Notes

- Expressions are loaded from the model's `按键/` folder (or `expressions/` for standard models)
- Files use `.exp3.json` format
- Expression names are extracted from filenames (e.g., `生气.exp3.json` → `生气`)
- The Live2D model's `SetExpression()` method is called with the expression name
