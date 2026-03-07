# OpenClaw 集成指南 - 雪莉桌面精灵控制接口

> 本文档面向 OpenClaw (或其他外部系统) 开发者，说明如何通过 HTTP API 控制雪莉的语音、情感和动作。

---

## 📡 接口概述

雪莉提供两个控制通道：

| 接口类型 | 地址 | 端口 | 用途 |
|---------|------|------|------|
| **HTTP API** | `127.0.0.1` | **8766** | OpenClaw 推荐使用的 REST 接口 |
| WebSocket | `127.0.0.1` | 8765 | 实时双向通信（可选） |

**OpenClaw 推荐使用 HTTP API**，简单易用，无需维护长连接。

---

## 🔌 基础连接测试

```bash
# 健康检查 - 确认雪莉运行正常
curl http://127.0.0.1:8766/health
```

**预期响应：**
```json
{
  "status": "ok",
  "websocket_connected": true,
  "current_mood": "happy",
  "affection": 65,
  "is_idle": false,
  "tts_enabled": true
}
```

---

## 🗣️ 一、语音控制 (TTS)

### 1.1 让雪莉说话

```bash
curl -X POST http://127.0.0.1:8766/api/command \
  -H "Content-Type: application/json" \
  -d '{
    "type": "speak",
    "data": {
      "text": "你好，我是雪莉！"
    }
  }'
```

**参数说明：**
- `text` (必填): 要说的话，支持中文
- 雪莉说话时**会自动注视前方**（临时禁用鼠标跟随）
- 语音结束后自动恢复鼠标跟随

**示例响应：**
```json
{"success": true, "message": "Command 'speak' sent"}
```

### 1.2 TTS 开关控制

```bash
# 关闭语音（雪莉只会动嘴型，不发声）
curl -X POST http://127.0.0.1:8766/api/tts \
  -H "Content-Type: application/json" \
  -d '{"action": "off"}'

# 开启语音
curl -X POST http://127.0.0.1:8766/api/tts \
  -H "Content-Type: application/json" \
  -d '{"action": "on"}'

# 切换开关状态
curl -X POST http://127.0.0.1:8766/api/tts \
  -H "Content-Type: application/json" \
  -d '{"action": "toggle"}'

# 查询当前状态
curl -X POST http://127.0.0.1:8766/api/tts \
  -H "Content-Type: application/json" \
  -d '{"action": "status"}'
```

---

## 😊 二、情感控制（表情）

### 2.1 切换表情

```bash
curl -X POST http://127.0.0.1:8766/api/command \
  -H "Content-Type: application/json" \
  -d '{
    "type": "expression",
    "data": {
      "name": "星星眼"
    }
  }'
```

### 2.2 可用表情列表

**常用表情（花丸模型）：**

| 表情名称 | 说明 | 适用场景 |
|---------|------|---------|
| `生气` | 生气/愤怒 | 被批评时 |
| `哭哭` | 哭泣/伤心 | 委屈时 |
| `星星眼` | 星星眼/兴奋 | 开心、期待 |
| `挥手` | 挥手打招呼 | 问候 |
| `红脸` / `blush` | 脸红/害羞 | 被夸奖时 |
| `变Q` / `q_style` | Q版/变小 | 卖萌 |
| `呆` / `daze` | 发呆/茫然 | 困惑时 |
| `黑脸` | 黑化/生气 | 不满 |
| `happy` | 开心/微笑 | 默认愉快 |
| `love` | 爱心/喜欢 | 表达好感 |
| `heart` | 比心 | 表达爱意 |
| `angry` | 愤怒 | 生气 |
| `normal` | 普通/默认 | 恢复常态 |

**模糊匹配支持：**
- 发送 `"星"` 会自动匹配 `"星星眼"`
- 发送 `"挥"` 会自动匹配 `"挥手"`

---

## 🎬 三、动作控制

### 3.1 触发动作

```bash
curl -X POST http://127.0.0.1:8766/api/command \
  -H "Content-Type: application/json" \
  -d '{
    "type": "motion",
    "data": {
      "group": "tap",
      "index": 0,
      "priority": 2
    }
  }'
```

### 3.2 动作组说明

| 动作组 | 说明 | 用途 |
|-------|------|------|
| `idle` | 待机动画 | 空闲时播放 |
| `tap` / `Tap` | 点击响应 | 被触摸时 |
| `greeting` | 问候动作 | 打招呼 |
| `Idle` | 待机（首字母大写）| 系统空闲动画 |

**优先级：**
- `1` - Idle（最低，可被覆盖）
- `2` - Normal（默认）
- `3` - Force（最高，强制播放）

---

## 💬 四、显示气泡消息

```bash
curl -X POST http://127.0.0.1:8766/api/command \
  -H "Content-Type: application/json" \
  -d '{
    "type": "message",
    "data": {
      "text": "OpenClaw 连接成功！",
      "duration": 3000,
      "position": "top"
    }
  }'
```

**参数：**
- `text`: 显示的文字
- `duration`: 显示时长（毫秒），默认 5000
- `position`: 位置 (`top`, `bottom`)，默认 `top`

---

## 🧠 五、好感度系统（情绪引擎）

雪莉有内置的情绪引擎，会记录好感度（0-100）：

| 好感度 | 等级 | 描述 |
|-------|------|------|
| 0-30 | 傲娇 | 容易生气，说话带刺 |
| 30-60 | 害羞 | 容易脸红，说话结巴 |
| 60-80 | 开心 | 活泼开朗，喜欢互动 |
| 80-100 | 超喜欢 | 粘人，经常表白 |

**查询当前状态：**
```bash
curl http://127.0.0.1:8766/health
# 查看 affection 字段
```

---

## 📝 六、完整 Python 示例

```python
#!/usr/bin/env python3
"""OpenClaw 控制雪莉的示例代码"""

import requests
import json

BASE_URL = "http://127.0.0.1:8766"

class SherryController:
    """雪莉控制器"""
    
    def __init__(self, base_url=BASE_URL):
        self.base_url = base_url
    
    def speak(self, text: str) -> bool:
        """让雪莉说话"""
        resp = requests.post(f"{self.base_url}/api/command", json={
            "type": "speak",
            "data": {"text": text}
        })
        return resp.json().get("success", False)
    
    def set_expression(self, name: str) -> bool:
        """设置表情"""
        resp = requests.post(f"{self.base_url}/api/command", json={
            "type": "expression",
            "data": {"name": name}
        })
        return resp.json().get("success", False)
    
    def trigger_motion(self, group: str, priority: int = 2) -> bool:
        """触发动画"""
        resp = requests.post(f"{self.base_url}/api/command", json={
            "type": "motion",
            "data": {"group": group, "index": 0, "priority": priority}
        })
        return resp.json().get("success", False)
    
    def show_message(self, text: str, duration: int = 3000) -> bool:
        """显示气泡消息"""
        resp = requests.post(f"{self.base_url}/api/command", json={
            "type": "message",
            "data": {"text": text, "duration": duration}
        })
        return resp.json().get("success", False)
    
    def tts_on(self) -> bool:
        """开启语音"""
        resp = requests.post(f"{self.base_url}/api/tts", json={"action": "on"})
        return resp.json().get("success", False)
    
    def tts_off(self) -> bool:
        """关闭语音"""
        resp = requests.post(f"{self.base_url}/api/tts", json={"action": "off"})
        return resp.json().get("success", False)
    
    def get_status(self) -> dict:
        """获取雪莉状态"""
        resp = requests.get(f"{self.base_url}/health")
        return resp.json()


# ========== 使用示例 ==========

if __name__ == "__main__":
    sherry = SherryController()
    
    # 1. 检查连接
    status = sherry.get_status()
    print(f"雪莉状态: {status}")
    
    # 2. 打招呼
    sherry.set_expression("happy")
    sherry.speak("OpenClaw 你好呀！雪莉很高兴见到你！")
    
    # 3. 根据 OpenClaw 的不同状态做出反应
    # ...
    
    # 示例：OpenClaw 完成一个任务
    sherry.set_expression("星星眼")
    sherry.speak("OpenClaw 好厉害！任务完成啦！")
    sherry.trigger_motion("Tap")
    
    # 示例：OpenClaw 遇到错误
    # sherry.set_expression("哭哭")
    # sherry.speak("哎呀，OpenClaw 好像遇到了问题...")
```

---

## 🔧 七、错误处理

**常见错误响应：**

```json
// WebSocket 未连接
{"success": false, "error": "WebSocket not connected"}

// JSON 格式错误
{"success": false, "error": "Invalid JSON"}

// 缺少必要字段
{"success": false, "error": "Missing 'type' field"}
```

**HTTP 状态码：**
- `200` - 成功
- `400` - 请求格式错误
- `503` - WebSocket 未连接（雪莉本体未启动）
- `500` - 服务器内部错误

---

## 🚀 八、OpenClaw 集成建议

### 推荐调用时机

| OpenClaw 事件 | 建议操作 |
|--------------|---------|
| 启动完成 | 调用 `get_status()` 检查雪莉是否运行 |
| 任务开始 | `speak()` + `set_expression("happy")` |
| 任务完成 | `speak("任务完成!")` + `set_expression("星星眼")` + `trigger_motion("Tap")` |
| 遇到错误 | `speak("出错了...")` + `set_expression("哭哭")` |
| 用户交互 | `show_message()` 显示提示 |
| 长时间运行 | 定时 `speak()` 保持用户注意力 |

### 最佳实践

1. **先检查健康状态**，确认雪莉运行正常再发送命令
2. **命令间隔建议 > 100ms**，避免过于频繁的请求
3. **语音长度适中**，建议每次不超过 50 字
4. **表情与语音配合**，增强表达效果

---

*Made with 💜 for OpenClaw Integration*

*最后更新: 2026-03-04*
