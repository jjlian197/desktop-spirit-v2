# 🎭 雪莉表情系统开发指南 (For AI Agents)

> 本文档面向 AI 编程助手，帮助快速理解和使用雪莉的表情系统。

---

## 📋 快速概览

雪莉的表情系统分为两层：
- **代码层表情** (`EXPRESSION_PARAM_MAP`): 在 `live2d_view.py` 中定义的参数化表情
- **模型层表情**: Hanamaru 模型 `按键/` 文件夹中的 `.exp3.json` 文件

大部分情况下，你只需要使用**代码层表情**（英文名称），系统会自动映射到模型层的对应表情。

---

## 🎨 可用表情列表

### 基础表情（始终可用）

| 代码名 | 模型名 | 效果描述 |
|--------|--------|----------|
| `normal` | - | 默认普通表情 |
| `happy` | `happy` | 开心微笑（眼睛弯弯）|
| `sad` | `哭哭` | 难过哭泣 |
| `surprised` | `Key14` | 惊讶/惊吓 |
| `sleepy` | `Key15` | 困倦/疲倦 |

### 🚨 好感度解锁表情

| 代码名 | 模型名 | 解锁好感度 | 阶段描述 |
|--------|--------|-----------|----------|
| `angry` | `Key14` | < 30 | 傲娇阶段 |
| `blush` | `红脸` | 30-60 | 害羞阶段 |
| `daze` | `呆` | 30-60 | 害羞阶段 |
| `star_eye` | `星星眼` | 60-80 | 开心阶段 |
| `cat_paw` | `猫爪` | 60-80 | 开心阶段 |
| `heart` | `比心` | > 80 | 超喜欢阶段 |
| `cat_mouth` | `叼猫条` | > 80 | 超喜欢阶段 |
| `q_style` | `变Q` | > 80 | 超喜欢阶段 |
| `love` | `Key32` | > 80 | 爱心眼 |

> 💡 **好感度机制**: 每次触摸雪莉 +5 点好感度，闲置 5 分钟后每 5 分钟 -2 点（最低 10 点）

---

## 🔧 如何使用表情

### 方法 1: 通过 WebSocket 发送命令

```python
import asyncio
import websockets
import json

async def set_expression(name: str):
    """设置雪莉的表情"""
    uri = "ws://127.0.0.1:8765/sprite"
    async with websockets.connect(uri) as ws:
        await ws.send(json.dumps({
            "type": "expression",
            "data": {"name": name}
        }))
        response = await ws.recv()
        return json.loads(response)

# 使用示例
asyncio.run(set_expression("happy"))      # 开心
asyncio.run(set_expression("blush"))      # 脸红（需好感度 30+）
asyncio.run(set_expression("heart"))      # 比心（需好感度 80+）
```

### 方法 2: 通过大脑 HTTP API

```python
import requests

def set_expression(name: str):
    """通过大脑 API 设置表情"""
    resp = requests.post(
        "http://127.0.0.1:8766/api/command",
        json={
            "type": "expression",
            "data": {"name": name}
        }
    )
    return resp.json()

# 使用示例
set_expression("star_eye")  # 星星眼
```

### 方法 3: 在 SpriteBrain 中直接调用

```python
# 在 brain/sprite_brain.py 中
class SpriteBrain:
    async def some_interaction(self):
        # 直接设置表情
        await self.set_expression("happy")
        
        # 根据好感度获取随机解锁表情
        unlocked = self.mood.get_unlocked_expressions()
        # 返回如: ["呆", "红脸"]
        
        # 获取当前推荐表情
        current_expr = self.mood.get_current_expression()
```

---

## 🧠 智能表情推荐（根据场景）

根据 `sprite_brain.py` 中的 `_handle_touch_reaction` 方法，不同触摸部位推荐的表情：

```python
# 触摸不同部位的推荐表情映射
TOUCH_EXPRESSIONS = {
    "head": "happy",           # 摸头 → 开心
    "cheek": "blush",          # 摸脸 → 脸红（敏感）
    "ear": "blush",            # 摸耳朵 → 脸红（敏感）
    "tail": "daze",            # 摸尾巴 → 发呆
    "hand": "heart",           # 握手 → 比心（高好感度）
    "default": "happy",        # 其他 → 开心
}

# 好感度等级对应的随机表情
AFFECTION_EXPRESSIONS = {
    (0, 30):   ["angry", "normal"],           # 傲娇
    (30, 60):  ["daze", "blush"],             # 害羞
    (60, 80):  ["happy", "star_eye", "cat_paw"],  # 开心
    (80, 101): ["love", "cat_mouth", "q_style"],  # 超喜欢
}
```

---

## 📊 好感度系统详解

### MoodEngine 配置

```python
# 好感度等级配置 (mood_engine.py)
AFFECTION_UNLOCKS = {
    (0, 30): {
        "moods": ["angry", "normal"],
        "expressions": ["生气", "黑脸"],
        "desc": "傲娇"
    },
    (30, 60): {
        "moods": ["blush", "daze", "normal"],
        "expressions": ["呆", "红脸"],
        "desc": "害羞"
    },
    (60, 80): {
        "moods": ["happy", "star_eye", "cat_paw"],
        "expressions": ["星星眼", "猫爪"],
        "desc": "开心"
    },
    (80, 101): {
        "moods": ["excited", "heart", "cat_mouth", "q_style"],
        "expressions": ["比心", "叼猫条", "变Q", "love"],
        "desc": "超喜欢"
    }
}
```

### 获取当前好感度信息

```python
# 获取当前等级描述
desc = self.mood.get_affection_desc()  # 返回: "傲娇"/"害羞"/"开心"/"超喜欢"

# 获取解锁的表情列表
expressions = self.mood.get_unlocked_expressions()  # 返回中文名列表

# 获取当前推荐的心情
mood = self.mood.get_random_unlocked_mood()
```

---

## ⚠️ 重要注意事项

### 1. 表情名称区分
- **代码层使用英文**: `happy`, `blush`, `star_eye`
- **模型层使用中文**: `红脸`, `星星眼`, `猫爪`
- `EXPRESSION_PARAM_MAP` 负责将英文映射到模型参数或按键名

### 2. 复合表情
部分表情需要同时设置多个参数（如 `happy`）：

```python
EXPRESSION_PARAM_MAP = {
    "happy": [("ParamEyeLSmile", 1.0), ("ParamEyeRSmile", 1.0)],  # 列表 = 复合
    "sad": "Key20",  # 字符串 = 单一按键
}
```

### 3. 好感度检查
在调用表情前，建议检查当前好感度：

```python
async def safe_set_expression(self, expr_name: str):
    """安全设置表情（检查好感度解锁）"""
    # 获取解锁的表情（中文名）
    unlocked = self.mood.get_unlocked_expressions()
    
    # 需要映射到中文进行比较
    name_mapping = {
        "blush": "红脸",
        "star_eye": "星星眼",
        "heart": "比心",
        # ... 其他映射
    }
    
    if name_mapping.get(expr_name) in unlocked:
        await self.set_expression(expr_name)
    else:
        # 好感度不足，使用默认表情
        await self.set_expression("happy")
```

### 4. 避免闪烁
不要频繁切换表情（间隔建议 > 1秒），否则会导致 Live2D 模型闪烁。

---

## 🔍 调试技巧

### 查看可用表情
```python
# 获取所有可用表情
available = live2d_view.get_available_expressions()
# 返回: ["normal", "happy", "sad", "angry", "love", "blush", ...]
```

### 日志追踪
```python
from loguru import logger

# 表情切换会输出日志
# [INFO] Setting expression (Param-based): happy
# [INFO] 雪莉的心情变更为: happy
```

### 测试 WebSocket
```bash
# 使用 wscat 或 websocat 测试
websocat ws://127.0.0.1:8765/sprite
# 然后输入: {"type": "expression", "data": {"name": "happy"}}
```

---

## 📁 相关文件

| 文件 | 说明 |
|------|------|
| `src/core/live2d_view.py` | `EXPRESSION_PARAM_MAP` 定义，表情参数映射 |
| `src/brain/mood_engine.py` | 好感度系统，情绪状态管理 |
| `src/brain/sprite_brain.py` | `_handle_touch_reaction()` 触摸表情反应 |
| `src/core/websocket_server.py` | WebSocket 表情命令处理 |
| `docs/EXPRESSIONS.md` | 完整的模型层表情列表（中文）|

---

## 💡 最佳实践

1. **优先使用英文代码名**: 如 `happy` 而不是 `开心`
2. **考虑好感度限制**: 高好感度表情（如 `heart`）在低好感度时会失败
3. **配合台词使用**: 切换表情后配合 `speak()` 效果更佳
4. **触摸反馈**: 不同部位使用不同表情，增加互动感
5. **闲置恢复**: 长时间无交互后，使用 `self.mood.update()` 自动降低好感度

---

*Made with 💜 for Master*  
*最后更新: 2026-03-02*
