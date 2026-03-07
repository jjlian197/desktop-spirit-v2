# 背景切换功能文档 (Background Switching)

> 本文档描述雪莉桌面精灵的背景切换功能的 API 使用方式和技术实现。

---

## 功能概述

背景切换功能允许用户动态修改精灵窗口的背景样式，支持以下类型：
- **透明背景** - 完全透明，可以看到桌面
- **纯色背景** - 任意 CSS 颜色值
- **渐变背景** - 内置紫色渐变或自定义 QSS 渐变
- **图片背景** - 本地图片作为背景

---

## API 接口

### 方法签名

```python
@pyqtSlot(str)
def set_background(self, bg_type: str)
```

**参数说明：**

| 参数 | 类型 | 说明 |
|------|------|------|
| `bg_type` | `str` | 背景类型标识符，支持预设关键字或自定义值 |

**调用方式：**

```python
# 通过窗口实例调用
window.set_background("purple")
```

---

## 支持的背景类型

### 1. 透明背景 (Transparent)

```python
set_background("transparent")
```

- 窗口背景完全透明
- 可以看到桌面和其他窗口
- 默认初始状态

---

### 2. 渐变紫色 (Purple Gradient)

```python
set_background("purple")
```

- 内置的紫蓝渐变背景
- 使用 QSS `qlineargradient` 实现
- 圆角 20px

**颜色值：**
- 起始色：`#667eea` (淡紫)
- 结束色：`#764ba2` (深紫)

---

### 3. 纯色背景 (Solid Color)

```python
# CSS 颜色名称
set_background("white")
set_background("black")
set_background("red")

# 十六进制颜色
set_background("#ff0000")
set_background("#667eea")

# RGB 格式
set_background("rgb(255, 0, 0)")
```

- 支持任意有效的 CSS 颜色值
- 自动应用圆角 20px

---

### 4. 图片背景 (Image)

```python
# 绝对路径
set_background("image:/Users/username/Pictures/bg.png")

# 使用 ~ 展开为用户目录
set_background("image:~/Pictures/my_bg.jpg")

# Windows 路径（自动转换）
set_background("image:C:\\Users\\name\\Pictures\\bg.png")
```

**特性：**
- 使用 `border-image` 样式填充
- 自动拉伸适应窗口大小
- 支持 `~` 展开为家目录
- 自动处理路径分隔符

---

## 使用示例

### 示例 1：基础切换

```python
from src.core.sprite_window import SherrySpriteWindow

window = SherrySpriteWindow()

# 切换到紫色渐变
window.set_background("purple")

# 切换到透明
window.set_background("transparent")

# 切换到白色背景
window.set_background("white")
```

### 示例 2：通过 WebSocket 控制

```python
import asyncio
import websockets
import json

async def change_background():
    async with websockets.connect('ws://127.0.0.1:8765/sprite') as ws:
        await ws.send(json.dumps({
            'type': 'set_background',
            'data': {'bg_type': 'purple'}
        }))

asyncio.run(change_background())
```

### 示例 3：HTTP API 调用

```bash
# 切换到紫色渐变
curl -X POST http://127.0.0.1:8766/api/command \
  -H "Content-Type: application/json" \
  -d '{"type": "set_background", "data": {"bg_type": "purple"}}'

# 切换到图片背景
curl -X POST http://127.0.0.1:8766/api/command \
  -H "Content-Type: application/json" \
  -d '{"type": "set_background", "data": {"bg_type": "image:~/Pictures/bg.png"}}'
```

---

## 右键菜单操作

用户可通过右键菜单快速切换背景：

1. **右键点击**精灵窗口
2. 选择 **"背景 (Background)"** 子菜单
3. 选择预设选项：
   - 透明 (Transparent)
   - 渐变紫 (Purple Gradient)

---

## 技术实现

### 核心代码

```python
@pyqtSlot(str)
def set_background(self, bg_type: str):
    """设置窗口背景 - 支持纯色、渐变、透明和本地图片路径"""
    
    if bg_type == "purple":
        # 渐变紫色
        self.central_widget.setStyleSheet("""
            #centralWidget {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
                    stop:0 #667eea, stop:1 #764ba2);
                border-radius: 20px;
            }
        """)
        
    elif bg_type == "transparent":
        # 透明背景
        self.central_widget.setStyleSheet(
            "#centralWidget { background: transparent; }"
        )
        
    elif bg_type.startswith("image:"):
        # 图片背景
        image_path = bg_type[6:]
        abs_path = Path(image_path).expanduser().resolve()
        
        if not abs_path.exists():
            logger.error(f"背景图片不存在: {abs_path}")
            return
            
        safe_path = str(abs_path).replace('\\\\', '/')
        style = f"""
            #centralWidget {{
                border-image: url("{safe_path}") 0 0 0 0 stretch stretch;
                border-radius: 20px;
            }}
        """
        self.central_widget.setStyleSheet(style)
        
    else:
        # 纯色背景
        self.central_widget.setStyleSheet(
            f"#centralWidget {{ background: {bg_type}; border-radius: 20px; }}"
        )
```

### 实现要点

1. **作用于 `central_widget`**
   - 不直接修改窗口背景，而是修改中心部件
   - 避免影响 Live2D OpenGL 渲染

2. **QSS 样式表**
   - 使用 Qt StyleSheet 设置背景
   - 支持 `qlineargradient` 渐变
   - 支持 `border-image` 图片填充

3. **路径处理**
   ```python
   # 展开用户目录 (~)
   abs_path = Path(image_path).expanduser().resolve()
   
   # 统一路径分隔符（Windows 兼容）
   safe_path = str(abs_path).replace('\\\\', '/')
   ```

4. **OpenGL 透明配合**
   ```python
   # Live2DView 设置透明属性
   self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
   self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, False)
   ```

---

## 扩展开发

### 添加新的预设背景

在 `sprite_window.py` 的 `set_background` 方法中添加新分支：

```python
elif bg_type == "dark":
    # 深色渐变
    self.central_widget.setStyleSheet("""
        #centralWidget {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #232526, stop:1 #414345);
            border-radius: 20px;
        }
    """)
    
elif bg_type == "pink":
    # 粉色渐变
    self.central_widget.setStyleSheet("""
        #centralWidget {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                stop:0 #ff9a9e, stop:1 #fecfef);
            border-radius: 20px;
        }
    """)
```

---

## 注意事项

1. **图片路径**
   - 使用绝对路径或带 `~` 的相对路径
   - 路径中的反斜杠会被自动转换为正斜杠

2. **样式优先级**
   - 样式表通过 `#centralWidget` ID 选择器应用
   - 确保 `central_widget` 的 `objectName` 为 `"centralWidget"`

3. **性能考虑**
   - 图片背景会使用更多内存
   - 大图片建议先压缩至窗口尺寸（400x600）

4. **兼容性**
   - 需要 PyQt6 支持
   - 透明背景需要 OpenGL 配合

---

## 相关文件

| 文件 | 说明 |
|------|------|
| `src/core/sprite_window.py` | 主实现文件，`set_background` 方法 |
| `src/core/live2d_view.py` | OpenGL 渲染，透明背景支持 |
| `config.yaml` | 默认配置（无背景配置项，运行时动态设置） |

---

*文档版本: 1.0*  
*最后更新: 2026-03-07*
