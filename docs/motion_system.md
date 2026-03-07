# 🎬 动作系统实现文档

> 本文档详细说明桌面精灵（Desktop Spirit）动作功能的架构设计与实现细节。

## 目录

- [架构概览](#架构概览)
- [核心模块](#核心模块)
  - [MotionPlayer - 手动动画播放器](#motionplayer---手动动画播放器)
  - [Live2DView - 动作触发与渲染](#live2dview---动作触发与渲染)
  - [SpriteBrain - 大脑逻辑控制](#spritebrain---大脑逻辑控制)
  - [WebSocketServer - 远程命令接口](#websocketserver---远程命令接口)
- [关键设计要点](#关键设计要点)
- [动作文件组织](#动作文件组织)
- [使用示例](#使用示例)

---

## 架构概览

动作功能由四个核心模块协同实现：

```
┌─────────────────┐     WebSocket      ┌──────────────────┐
│  SpriteBrain    │ ◄────────────────► │ WebSocketServer  │
│  (大脑/逻辑层)   │                    │   (命令接口)      │
└────────┬────────┘                    └────────┬─────────┘
         │                                      │
         │  trigger_motion("Tap")              │ QMetaObject.invokeMethod
         ▼                                      ▼
┌─────────────────────────────────────────────────────────┐
│                      Live2DView                          │
│                   (OpenGL 渲染层)                         │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐ │
│  │ StartMotion │    │ MotionPlayer │   │ 参数化控制   │ │
│  │ (原生SDK)   │    │ (备选方案)  │    │ (表情/眼神) │ │
│  └─────────────┘    └─────────────┘    └─────────────┘ │
└─────────────────────────────────────────────────────────┘
```

### 数据流向

1. **触发源**：用户触摸、空闲检测、外部命令
2. **逻辑层**：`SpriteBrain` 决定播放什么动作
3. **传输层**：`WebSocketServer` 将命令转发到主线程
4. **渲染层**：`Live2DView` 调用 Live2D SDK 或 MotionPlayer 执行动画

---

## 核心模块

### MotionPlayer - 手动动画播放器

**文件位置**: `src/core/motion_player.py`

#### 功能说明

`MotionPlayer` 是一个自定义的动画播放器，用于直接解析 Live2D 的 `motion3.json` 文件并手动控制参数变化。它作为 **StartMotion 的备选方案**，在原生 SDK 动画不可用时使用。

#### 核心原理

```python
class MotionPlayer:
    def __init__(self, param_setter: Callable[[str, float], None]):
        """
        Args:
            param_setter: 参数设置回调函数 (param_id, value) -> None
        """
        self.param_setter = param_setter
```

#### 动画播放流程

```python
def _play_loop(self, motion_data: Dict, loop: bool):
    """播放循环 - 按时间轴插值计算参数值"""
    meta = motion_data.get("Meta", {})
    duration = meta.get("Duration", 6.0)  # 动画时长
    fps = meta.get("Fps", 60.0)
    curves = motion_data.get("Curves", [])  # 参数曲线列表
    
    start_time = time.time()
    
    while not self._stop_event.is_set():
        elapsed = time.time() - start_time
        if elapsed > duration:
            break
        
        # 计算当前时间点所有参数的值
        for curve in curves:
            param_id = curve.get("Id")
            segments = curve.get("Segments", [])
            value = self._interpolate_value(elapsed, segments)
            self.param_setter(param_id, value)  # 设置到模型
        
        time.sleep(1/30)  # 控制 30fps
```

#### 插值算法

支持两种动画曲线类型：

| 类型 | 格式 | 说明 |
|------|------|------|
| **线性** | `[0, time, value]` | 直线插值 |
| **贝塞尔** | `[1, time, value, cp1x, cp1y, cp2x, cp2y]` | 曲线插值 |

```python
def _interpolate_value(self, time: float, segments: List) -> float:
    """根据时间插值计算参数值"""
    # 解析时间段
    points = []
    i = 0
    while i < len(segments):
        seg_type = segments[i]
        if seg_type == 0:  # 线性段
            t = segments[i + 1]
            v = segments[i + 2]
            points.append((t, v))
            i += 3
        elif seg_type == 1:  # 贝塞尔段
            t = segments[i + 1]
            v = segments[i + 2]
            points.append((t, v))
            i += 7
    
    # 找到当前时间所在的段并插值
    for i in range(len(points) - 1):
        t1, v1 = points[i]
        t2, v2 = points[i + 1]
        if t1 <= time <= t2:
            t = (time - t1) / (t2 - t1)
            return v1 + (v2 - v1) * t
```

---

### Live2DView - 动作触发与渲染

**文件位置**: `src/core/live2d_view.py`

#### 功能说明

`Live2DView` 是动作执行的核心渲染层，负责：
- 调用 Live2D SDK 的 `StartMotion` 播放动画
- 管理 `MotionPlayer` 作为备选方案
- 控制动作播放状态（暂停/恢复鼠标跟随）

#### 动作触发方式

##### A. 原生 StartMotion（主要方式）

```python
def trigger_motion(self, group: str, index: int = 0, force: bool = True):
    """
    触发动画/动作
    
    Args:
        group: 动作组名（如 "Tap", "Idle"）
        index: 动作索引
        force: 是否强制播放（默认True）
               - True: 使用 FORCE 优先级，打断当前动画
               - False: 使用 NORMAL 优先级，避免打断 Idle 循环
    """
    # 检查是否已在播放相同动作（避免 Idle 循环被打断）
    if not force and self._motion_playing and self._current_motion_group == group:
        logger.debug(f"Motion '{group}' already playing, skipping")
        return True
    
    # 判断是否为待机动画
    is_idle = group.lower() == "idle"
    
    # 选择优先级
    priority = live2d.MotionPriority.FORCE if force else live2d.MotionPriority.NORMAL
    
    # 调用 Live2D SDK
    result = self.model.StartMotion(group, index, priority)
    
    # 记录状态
    self._current_motion_group = group
    
    # 非待机动画暂停鼠标跟随
    if not is_idle:
        self._motion_playing = True
        self._motion_playing_timer.start(100)
```

##### B. MotionPlayer 备选方案

```python
def _preload_motions(self, model_dir: Path):
    """预加载动作文件 - 用于 MotionPlayer 备选方案"""
    if not HAS_MOTION_PLAYER:
        return
    
    motion_mapping = {
        "Tap": "Tap.motion3.json",
        "Idle": "Idle.motion3.json"
    }
    
    # 初始化 MotionPlayer
    self._motion_player = MotionPlayer(self._set_motion_param)
    
    for group_name, filename in motion_mapping.items():
        motion_file = model_dir / filename
        if motion_file.exists():
            self._motion_files[group_name] = motion_file

def _set_motion_param(self, param_id: str, value: float):
    """MotionPlayer 的参数设置回调"""
    if self.model and HAS_LIVE2D:
        self.model.SetParameterValue(param_id, value)
```

#### 动作播放状态管理

```python
def _check_motion_finished(self):
    """检查动作是否播放完成"""
    if not self.model or not HAS_LIVE2D:
        self._motion_playing = False
        return
    
    try:
        # 检查是否有动作正在播放
        if self.model.IsMotionFinished():
            current_group = getattr(self, '_current_motion_group', None)
            
            # 只有非 Idle 动画才重置 _motion_playing
            if current_group and current_group.lower() != "idle":
                self._motion_playing = False
                logger.debug("Motion finished, resuming mouse follow")
            
            self._current_motion_group = None
            self._motion_playing_timer.stop()
    except Exception as e:
        logger.debug(f"Check motion status failed: {e}")
        self._motion_playing = False
```

#### 动态动作组映射

在加载模型时，自动修改 `model3.json` 添加动作组映射：

```python
def _prepare_model_json_with_motions(self, model_dir: Path, original_json: Path) -> Path:
    """动态修改 model3.json 添加动作组映射"""
    
    # 读取原始 model3.json
    with open(original_json, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # 确保 Motions 存在
    if 'Motions' not in data['FileReferences']:
        data['FileReferences']['Motions'] = {}
    
    motions = data['FileReferences']['Motions']
    
    # 定义动作映射
    motion_mapping = {
        "Tap": "Tap.motion3.json",
        "Idle": "Idle.motion3.json"
    }
    
    # 添加动作组
    for group_name, motion_file in motion_mapping.items():
        motion_path = model_dir / motion_file
        if motion_path.exists():
            if group_name not in motions:
                motions[group_name] = []
            motions[group_name].append({"File": motion_file})
    
    # 保存临时文件
    temp_json = model_dir / f"_temp_with_motions_{original_json.name}"
    with open(temp_json, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    return temp_json
```

---

### SpriteBrain - 大脑逻辑控制

**文件位置**: `src/brain/sprite_brain.py`

#### 功能说明

`SpriteBrain` 是动作系统的逻辑决策层，负责：
- 响应触摸事件并触发相应动作
- 管理空闲状态下的待机动画
- 协调表情和动作的配合

#### 触摸触发动画

```python
async def _handle_touch(self, action: str, part: str):
    """处理触摸，产生情绪和反馈"""
    
    # 定义分区反馈
    part_reactions = {
        "头顶": {
            "expression": "happy",
            "motion": "Tap",        # ← 触发 Tap 动作
            "responses": ["被主人摸头了...好幸福..."]
        },
        "脸颊": {
            "expression": "blush",
            "motion": "Tap",
            "responses": ["主、主人...捏雪莉的脸..."]
        },
        "身体": {
            "expression": "blush",
            "motion": "Idle",       # ← 触发 Idle 动作
            "responses": ["呀！那里好敏感..."]
        },
        "左手": {
            "expression": "love",
            "motion": "Tap",
            "responses": ["主人握住了雪莉的手..."]
        },
        "右手": {
            "expression": "love",
            "motion": "Idle",
            "responses": ["手拉手～好开心～"]
        },
        "尾巴": {
            "expression": "happy",
            "motion": "Idle",
            "responses": ["尾巴被抓住了！"]
        },
    }
    
    # 获取对应部位的反应
    reaction = part_reactions.get(part, part_reactions["身体"])
    
    # 设置表情
    await self.set_expression(expression)
    
    # 触发动画
    try:
        motion_result = await self.trigger_motion(reaction["motion"])
    except Exception as e:
        logger.debug(f"Motion trigger failed (optional): {e}")
```

#### 空闲动画系统

```python
async def _idle_loop(self):
    """空闲检测与待机动画循环"""
    
    while self.running:
        idle_time = time.time() - self.last_interaction_time
        
        # 判断是否进入空闲状态
        if idle_time >= self.idle_config["idle_timeout"] and not self.is_idle:
            self.is_idle = True
            logger.info(f"进入空闲状态（已闲置 {idle_time:.1f} 秒）")
        
        # 空闲状态下播放待机动画
        if self.is_idle and not self.idle_motion_playing:
            self.idle_motion_playing = True
            
            # 使用 force=False 避免重复打断
            try:
                result = await self.trigger_motion("Idle", interactive=False, force=False)
            except Exception as e:
                logger.error(f"待机动画异常: {e}")
            
            # 等待间隔时间
            await asyncio.sleep(self.idle_config["motion_interval"])
            self.idle_motion_playing = False
            
            # 随机眨眼（30%概率）
            if self.idle_config["random_blink"] and random.random() < 0.3:
                await self.send_command("parameter_batch", {
                    "params": {"ParamEyeLOpen": 0.0, "ParamEyeROpen": 0.0}
                })
                await asyncio.sleep(0.15)
                await self.send_command("parameter_batch", {
                    "params": {"ParamEyeLOpen": 1.0, "ParamEyeROpen": 1.0}
                })
        
        await asyncio.sleep(0.5)
```

#### 动作触发接口

```python
async def trigger_motion(self, group: str, interactive: bool = True, force: bool = True):
    """
    触发动作
    
    Args:
        group: 动作组名
        interactive: 是否为用户交互（会影响空闲计时器）
        force: 是否强制播放。对于循环动作如 Idle，设为 False 可避免重复触发
    """
    if interactive:
        self.reset_idle_timer("motion")  # 重置空闲计时
    
    return await self.send_command("motion", {"group": group, "force": force})
```

---

### WebSocketServer - 远程命令接口

**文件位置**: `src/core/websocket_server.py`

#### 功能说明

`WebSocketServer` 提供外部控制接口，接收来自 `SpriteBrain` 或其他客户端的命令，并线程安全地转发到 `Live2DView`。

#### 动作命令处理

```python
async def _handle_motion(self, data: dict, websocket):
    """Handle motion trigger request"""
    group = data.get("group", "tap")
    index = data.get("index", 0)
    priority = data.get("priority", 2)
    
    # 从请求中读取 force 参数，默认为 True
    force = data.get("force", True)
    
    # 如果没有指定 force 且是 Idle 动作，自动设为 False
    if "force" not in data and group.lower() == "idle":
        force = False
    
    # 线程安全地调用 Qt 方法
    QMetaObject.invokeMethod(
        self.sprite_window,
        "trigger_motion",
        Qt.ConnectionType.QueuedConnection,
        Q_ARG(str, group),
        Q_ARG(int, index),
        Q_ARG(bool, force)
    )
    
    await self._send_response(websocket, "motion_triggered", {
        "group": group, 
        "index": index, 
        "force": force
    })
```

#### 消息协议

**请求格式**:
```json
{
    "type": "motion",
    "data": {
        "group": "Tap",
        "index": 0,
        "force": true
    }
}
```

**响应格式**:
```json
{
    "type": "motion_triggered",
    "data": {
        "group": "Tap",
        "index": 0,
        "force": true
    },
    "success": true
}
```

---

## 关键设计要点

### 1. 动作优先级控制

| 优先级 | 枚举值 | 说明 |
|--------|--------|------|
| **NORMAL** | `live2d.MotionPriority.NORMAL` | 普通优先级，不打断当前动画 |
| **FORCE** | `live2d.MotionPriority.FORCE` | 强制优先级，打断当前动画 |

```python
# 用户触发的动作使用 FORCE
await self.trigger_motion("Tap", force=True)

# 空闲动画使用 NORMAL，避免互相打断
await self.trigger_motion("Idle", force=False)
```

### 2. 鼠标跟随暂停机制

动作播放期间需要暂停鼠标跟随，避免参数冲突：

```python
# Live2DView 中检查动作播放状态
def _get_mouse_follow_params(self) -> dict:
    # 如果动作正在播放，暂停鼠标跟随参数设置
    if self._motion_playing:
        return {}
    # ... 计算鼠标跟随参数
```

**例外**：待机动画（Idle）不暂停鼠标跟随，保持自然效果。

### 3. 重复触发保护

避免相同的 Idle 动画被重复触发：

```python
def trigger_motion(self, group: str, index: int = 0, force: bool = True):
    # 检查是否已经在播放相同的动作
    if not force and self._motion_playing and self._current_motion_group == group:
        logger.debug(f"Motion '{group}' already playing, skipping")
        return True
```

### 4. 跨线程安全

所有 UI 操作通过 `QMetaObject.invokeMethod` 在主线程执行：

```python
QMetaObject.invokeMethod(
    self.sprite_window,
    "trigger_motion",
    Qt.ConnectionType.QueuedConnection,  # 队列连接，确保线程安全
    Q_ARG(str, group),
    Q_ARG(int, index),
    Q_ARG(bool, force)
)
```

### 5. 动作文件动态映射

无需手动修改 `model3.json`，系统自动添加动作组映射：

```python
# 自动添加以下映射
motion_mapping = {
    "Tap": "Tap.motion3.json",
    "Idle": "Idle.motion3.json"
}
```

---

## 动作文件组织

### 目录结构

```
模型目录/
├── model3.json              # 模型配置文件（会被自动修改）
├── _temp_with_motions_*.json # 自动生成的临时配置文件
├── Tap.motion3.json         # 触摸动作（摸摸头）
├── Idle.motion3.json        # 待机动画（呼吸/摇晃）
└── ...                      # 其他动作文件
```

### 动作文件格式

`motion3.json` 是 Live2D 的标准动画格式，包含：

```json
{
  "Version": 3,
  "Meta": {
    "Duration": 6.0,      // 动画时长（秒）
    "Fps": 60.0,          // 帧率
    "Loop": true          // 是否循环
  },
  "Curves": [             // 参数曲线数组
    {
      "Id": "ParamAngleX",  // 参数 ID
      "Segments": [         // 时间段定义
        0, 0.0, 0.0,        // [类型, 时间, 值]
        0, 1.0, 10.0,       // 线性段
        0, 2.0, 0.0
      ]
    },
    {
      "Id": "ParamAngleY",
      "Segments": [
        1, 0.0, 0.0, 0.0, 0.0, 0.5, 1.0,  // 贝塞尔段
        0, 1.0, 5.0
      ]
    }
  ]
}
```

### 常用参数 ID

| 参数 ID | 说明 | 范围 |
|---------|------|------|
| `ParamAngleX` | 头部左右旋转 | -30 ~ 30 |
| `ParamAngleY` | 头部上下旋转 | -30 ~ 30 |
| `ParamAngleZ` | 头部倾斜 | -30 ~ 30 |
| `ParamBodyAngleX` | 身体左右旋转 | -30 ~ 30 |
| `ParamBodyAngleY` | 身体前后倾斜 | -30 ~ 30 |
| `ParamBodyAngleZ` | 身体侧倾 | -30 ~ 30 |
| `ParamEyeBallX` | 眼球左右 | -1.0 ~ 1.0 |
| `ParamEyeBallY` | 眼球上下 | -1.0 ~ 1.0 |

---

## 使用示例

### 1. 通过 SpriteBrain 触发动画

```python
from src.brain.sprite_brain import SpriteBrain

brain = SpriteBrain()
await brain.start()

# 触发触摸动画
await brain.trigger_motion("Tap")

# 触发待机动画（不强制）
await brain.trigger_motion("Idle", force=False)
```

### 2. 通过 WebSocket 触发动画

```python
import websockets
import json

async with websockets.connect("ws://127.0.0.1:8765/sprite") as ws:
    # 发送动作命令
    await ws.send(json.dumps({
        "type": "motion",
        "data": {
            "group": "Tap",
            "force": True
        }
    }))
```

### 3. 直接调用 Live2DView

```python
from src.core.live2d_view import Live2DView

view = Live2DView()
view.load_model("path/to/model")

# 触发动画
view.trigger_motion("Tap", force=True)

# 设置参数（直接控制）
view.set_parameter("ParamAngleX", 15.0)
```

### 4. 批量设置参数（鼠标跟随）

```python
# 批量设置多个参数（高效）
params = {
    "ParamAngleX": 15.0,
    "ParamAngleY": -10.0,
    "ParamEyeBallX": 0.5,
    "ParamEyeBallY": 0.3
}
await brain.send_command("parameter_batch", {"params": params})
```

---

## 相关文件

| 文件 | 说明 |
|------|------|
| `src/core/motion_player.py` | 手动动画播放器 |
| `src/core/live2d_view.py` | Live2D 渲染与动作控制 |
| `src/brain/sprite_brain.py` | 大脑逻辑与动画决策 |
| `src/core/websocket_server.py` | WebSocket 命令接口 |

---

## 注意事项

1. **线程安全**：所有 UI 操作必须在主线程执行，使用 `QMetaObject.invokeMethod`
2. **Idle 特殊处理**：待机动画使用 `force=False`，避免重复打断
3. **鼠标跟随暂停**：非 Idle 动画播放时暂停鼠标跟随
4. **临时文件清理**：程序会自动清理生成的 `_temp_with_motions_*.json` 文件
5. **动作文件命名**：建议使用英文文件名避免编码问题
