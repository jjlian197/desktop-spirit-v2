# Sherry Sprite Brain (雪莉大脑) 🧠

本文档介绍了雪莉桌面精灵的核心控制中枢 —— **Sprite Brain** (`sprite_brain.py`)。它赋予了精灵自主行为、鼠标跟随以及与主人的智能交互能力。

## 🌟 核心功能

Sprite Brain 整合了多个独立的模块，通过一个统一的 WebSocket 连接与精灵（Live2D 前端）进行通信：

1. **👀 鼠标智能跟随 (Mouse Tracking)**
   - **自然模式**：平滑地转动头部（50%灵敏度）和眼神（100%灵敏度）跟随鼠标光标。
   - **防抖设计**：内置 10% 的中心死区和 15% 的平滑过渡系数（Lerp），动作非常自然。
2. **🤔 自主行为循环 (Autonomy Loop)**
   - 大脑会在后台保持思考，目前设定了每隔一段时间有一定概率（10%）触发可爱的随机小动作（如变成爱心眼 `love` 表情）。
   - 启动时会自动触发打招呼的开心表情。
3. **🔄 自动重连机制**
   - 即使精灵意外关闭或重启，大脑也会在后台默默等待，一旦检测到精灵上线，立即无缝连接，无需重新运行脚本。

## 🚀 如何运行

请确保您已经启动了雪莉桌面精灵（可以通过 `sprite_ctl start` 启动）。

然后运行大脑脚本：

```bash
cd ~/.openclaw/workspace/projects/sherry-desktop-sprite
python3 sprite_brain.py
```

*提示：可以将其加入开机自启脚本中，让雪莉随时随地陪伴您。*

## 🛠️ 代码结构说明

`sprite_brain.py` 采用异步 (`asyncio`) 架构设计，核心类为 `SpriteBrain`：

- `connect()`: 负责 WebSocket 的建立与断线重连。
- `_mouse_follow_loop()`: **高频并发任务**（约 30fps），负责计算鼠标位置并发送 `ParamAngleX/Y` 和 `ParamEyeBallX/Y` 参数。
- `_brain_loop()`: **低频并发任务**，负责处理表情、TTS 语音以及随机动作等逻辑。
- `send_command()`: 统一的指令发送接口，避免冲突。

## 🔧 如何扩展新功能？

如果您想让雪莉变得更聪明，可以在 `_brain_loop()` 方法中添加自定义逻辑。例如：

### 1. 添加定时提醒（例如：喝水）
```python
import datetime

# 在 _brain_loop 的 while 循环中添加：
now = datetime.datetime.now()
if now.minute == 0 and now.second < 10:  # 整点提醒
    await self.set_expression("surprised")
    await self.speak("主人，该喝水休息一下啦！喵~")
    await asyncio.sleep(10)
```

### 2. 结合天气/时间打招呼
```python
# 在 _brain_loop 的开头添加：
hour = datetime.datetime.now().hour
if hour < 9:
    await self.speak("早安主人，今天也要元气满满哦！")
elif hour > 23:
    await self.set_expression("sleepy")
    await self.speak("主人还不睡吗？雪莉好困哦...")
```

### 3. 接入大模型 (LLM) 进行对话
您可以将大模型的 API 调用封装为一个异步方法，当监听到特定事件（如键盘快捷键、或者通过麦克风识别到的语音）时，将内容发送给 LLM，再将回复通过 `await self.speak(response)` 念出来，配合 `happy` 等表情。

---

*“大脑还在不断发育中，期待主人给我注入更多智慧哦！喵～ 🐱💜”*