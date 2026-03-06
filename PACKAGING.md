# Windows 打包说明

## 环境准备

1. 安装 PyInstaller:
```bash
pip install pyinstaller
```

2. 确保所有依赖已安装:
```bash
pip install -r requirements.txt
```

## 打包方法

### 方法 1: 使用打包脚本 (推荐)

```bash
python build_exe.py
```

打包完成后，可执行文件位于 `dist/SherrySprite/SherrySprite.exe`

### 方法 2: 手动打包

```bash
pyinstaller --onedir --windowed --clean --noconfirm \
    --add-data "src/assets;src/assets" \
    --hidden-import PyQt6.sip \
    --hidden-import live2d.v3 \
    --hidden-import edge_tts \
    --hidden-import pydub \
    --hidden-import pygame \
    --hidden-import aiohttp \
    --hidden-import websockets \
    src/main.py
```

## 路径处理说明

打包后的路径处理已自动完成:

- **开发环境**: 使用相对路径 `src/assets/models/hanamaru`
- **打包后**: 使用 `sys._MEIPASS` 指向临时解压目录

关键修复:
1. ✅ `src/utils/__init__.py` - 添加 `get_resource_path()` 函数
2. ✅ `src/core/sprite_window.py` - 使用 `get_resource_path()` 加载模型
3. ✅ `src/core/sprite_window.py` - 添加 `closeEvent()` 清理资源

## 文件结构

打包后的目录结构:
```
dist/SherrySprite/
├── SherrySprite.exe      # 主可执行文件
├── src/                  # 资源文件 (由 --add-data 添加)
│   └── assets/
│       └── models/
│           └── hanamaru/
│               ├── model.moc3
│               ├── model.model3.json
│               ├── Tap.motion3.json      # 英文名动作文件
│               ├── Idle.motion3.json     # 英文名动作文件
│               └── textures/
├── _internal/            # PyInstaller 内部文件
└── 启动雪莉.bat         # 启动脚本
```

## 测试打包

1. 在开发环境运行正常:
```bash
python -m src.main
```

2. 打包后测试:
```bash
# 运行打包后的程序
dist\SherrySprite\SherrySprite.exe
```

## 注意事项

1. **模型路径**: 已修复为使用 `get_resource_path()`，自动处理打包前后路径差异
2. **临时文件**: 程序退出时会自动清理临时 model.json 文件
3. **日志文件**: 位于用户目录 `~/.sherry/sprite.log`
4. **TTS 缓存**: 使用系统临时目录，自动清理

## 常见问题

### 1. 打包后找不到模型文件
- 检查 `src/assets/models/hanamaru/` 是否存在
- 检查 `--add-data` 参数是否正确

### 2. 缺少 DLL 或依赖
- 添加 `--hidden-import` 参数
- 或使用 `--collect-all` 收集完整包

### 3. 启动慢
- 改用 `--onedir` 模式（单目录而非单文件）
- 已默认使用 `--onedir`

### 4. 图标不显示
- 准备 `icon.ico` 文件放在 `src/assets/`
- 取消注释 `build_exe.py` 中的图标行
