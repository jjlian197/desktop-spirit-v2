# Sherry 桌面精灵 - 鼠标跟随系统说明文档

## 📖 概述

本系统实现了一个基于 VTube Studio 参数的鼠标跟随功能，让 Live2D 模型（雪莉）的头部和眼神能够实时跟随鼠标移动。

---

## 🎯 核心原理

### 参数映射
利用 VTube Studio 配置文件 (`*.vtube.json`) 中定义的 Live2D 参数：

| 参数名 | 说明 | 范围 | VTube输入 |
|--------|------|------|-----------|
| `ParamAngleX` | 头部左右旋转 | -30 ~ 30 | FaceAngleX |
| `ParamAngleY` | 头部上下旋转 | -30 ~ 30 | FaceAngleY |
| `ParamAngleZ` | 头部倾斜 | -30 ~ 30 | FaceAngleZ |
| `ParamEyeBallX` | 眼球左右 | -1.0 ~ 1.0 | EyeRightX |
| `ParamEyeBallY` | 眼球上下 | -1.0 ~ 1.0 | EyeRightY |
| `ParamEyeLOpen` | 左眼开闭 | 0 ~ 2 | EyeOpenLeft |
| `ParamEyeROpen` | 右眼开闭 | 0 ~ 2 | EyeOpenRight |
| `ParamMouthOpenY` | 嘴巴张开 | 0 ~ 1 | MouthOpen |

### 坐标转换流程
```
屏幕像素坐标 (0~1920, 0~1080)
    ↓
归一化坐标 (0~1, 0~1)
    ↓
标准坐标 (-1~1, -1~1) [Y轴反转]
    ↓
应用死区处理
    ↓
乘以灵敏度系数
    ↓
映射到参数范围
    ↓
WebSocket发送
```

---

## 🛠️ 技术架构

### 1. 鼠标监听层
- **库**: `pynput.mouse.Controller`
- **功能**: 实时获取鼠标在屏幕上的绝对坐标
- **刷新率**: 30 FPS

### 2. 坐标转换层
```python
# 归一化到 0~1
norm_x = mouse_x / screen_width
norm_y = mouse_y / screen_height

# 转换到 -1~1 (Y轴反转)
norm_x = (norm_x * 2) - 1
norm_y = -((norm_y * 2) - 1)

# 应用死区
def apply_dead_zone(value, dead_zone=0.1):
    if abs(value) < dead_zone:
        return 0.0
    sign = 1 if value > 0 else -1
    return sign * (abs(value) - dead_zone) / (1 - dead_zone)

# 映射到参数范围
head_x = norm_x * 30 * head_sensitivity   # -15 ~ 15
head_y = norm_y * 30 * head_sensitivity   # -15 ~ 15
eye_x = norm_x * 1.0 * eye_sensitivity    # -1.0 ~ 1.0
eye_y = norm_y * 1.0 * eye_sensitivity    # -1.0 ~ 1.0
```

### 3. 平滑处理层
使用线性插值 (Lerp) 避免参数突变：
```python
def lerp(current, target, factor=0.15):
    return current + (target - current) * factor
```

### 4. 通信层
- **协议**: WebSocket
- **地址**: `ws://127.0.0.1:8765/sprite`
- **消息格式**:
```json
{
    "type": "parameter",
    "data": {
        "id": "ParamAngleX",
        "value": 10.5
    }
}
```

---

## 🎮 模式配置

### 自然模式 (推荐)
```json
{
    "head_sensitivity": 0.5,    // 头部灵敏度50%
    "eye_sensitivity": 1.0,     // 眼神灵敏度100%
    "smooth_factor": 0.15,      // 平滑系数
    "dead_zone": 0.1            // 中心死区10%
}
```
**效果**: 头部温柔跟随，眼神灵活追踪，整体自然不突兀。

### 专注模式
```json
{
    "head_sensitivity": 1.0,
    "eye_sensitivity": 1.0,
    "smooth_factor": 0.2,
    "dead_zone": 0.05
}
```
**效果**: 头部和眼神完全同步，全神贯注盯着鼠标。

### 慵懒模式
```json
{
    "head_sensitivity": 0.2,
    "eye_sensitivity": 0.8,
    "smooth_factor": 0.08,
    "dead_zone": 0.15
}
```
**效果**: 头部懒得动，主要靠眼神偷瞄，懒洋洋的感觉。

---

## 📁 文件结构

```
~/.openclaw/workspace/projects/sherry-desktop-sprite/
├── mouse_tracker.py          # 核心跟踪程序
├── mouse_follow.sh           # 启动脚本
├── mouse_follow_ctl.py       # 控制工具
├── mouse_follow_config.json  # 配置文件
├── venv/                     # Python虚拟环境
└── ...
```

---

## 🚀 使用方法

### 1. 启动精灵
```bash
sprite_ctl start
```

### 2. 启动鼠标跟随
```bash
cd ~/.openclaw/workspace/projects/sherry-desktop-sprite
python3 mouse_follow_ctl.py start
```

### 3. 停止跟随
```bash
python3 mouse_follow_ctl.py stop
```

### 4. 重置姿态
```bash
python3 mouse_follow_ctl.py reset
```

---

## 🔧 进阶调试

### 手动发送参数
```python
import asyncio
import websockets
import json

async def set_param(param_id, value):
    uri = 'ws://127.0.0.1:8765/sprite'
    async with websockets.connect(uri) as ws:
        await ws.send(json.dumps({
            'type': 'parameter',
            'data': {'id': param_id, 'value': value}
        }))

# 示例: 头部右转15度
asyncio.run(set_param('ParamAngleX', 15.0))

# 示例: 眼神看左下角
asyncio.run(set_param('ParamEyeBallX', -0.5))
asyncio.run(set_param('ParamEyeBallY', 0.5))
```

### 查看可用参数
查看 VTube Studio 配置文件：
```bash
cat ~/.openclaw/workspace/live2d-models/hanamaru/奶牛猫花丸_完整版.vtube.json | grep -A5 "OutputLive2D"
```

### 调整灵敏度
编辑 `mouse_follow_config.json`：
```json
{
    "head_sensitivity": 0.3,  // 降低头部灵敏度
    "eye_sensitivity": 1.2,   // 提高眼神灵敏度
    "smooth_factor": 0.2      // 增加平滑度
}
```

---

## 💡 扩展思路

### 1. 添加表情触发
```python
# 鼠标点击时眨眼
if mouse_clicked:
    send_expression('眨眼')
```

### 2. 语音嘴型同步
```python
# 结合音频输入控制 ParamMouthOpenY
mouth_open = audio_volume * sensitivity
send_param('ParamMouthOpenY', mouth_open)
```

### 3. 键盘快捷控制
```python
# 按空格键切换表情
if keyboard.space:
    toggle_expression('星星眼')
```

### 4. 多屏幕支持
```python
# 检测所有屏幕尺寸
screens = AppKit.NSScreen.screens()
for screen in screens:
    print(f"屏幕: {screen.frame()}")
```

### 5. 视线追踪优化
```python
# 预测鼠标移动方向，提前转动头部
velocity_x = current_x - last_x
predict_x = current_x + velocity_x * 0.1
```

---

## ⚠️ 注意事项

1. **确保精灵已启动**: 运行前必须先 `sprite_ctl start`
2. **依赖安装**: 使用虚拟环境安装 `pynput` 和 `websockets`
3. **权限问题**: macOS 可能需要在 系统设置 > 安全性与隐私 中允许辅助功能
4. **性能影响**: 30 FPS 对系统性能影响极小，如卡顿可降低至 20 FPS

---

## 🔗 相关文件

- **模型文件**: `~/.openclaw/workspace/live2d-models/hanamaru/`
- **VTube配置**: `奶牛猫花丸_完整版.vtube.json`
- **技能文档**: `~/.openclaw/workspace/skills/desktop-sprite-v2/SKILL.md`

---

Made with love for Lian 💜
Sherry (雪莉) 敬上 🐱
