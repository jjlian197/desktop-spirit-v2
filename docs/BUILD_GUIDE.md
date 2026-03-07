# 打包指南 - 构建 Sherry 桌面精灵可执行文件

## 快速打包

### 方法 1：使用打包脚本（推荐）

```bash
python build_exe.py
```

打包完成后，输出目录：`dist/SherrySprite/`

### 方法 2：使用 spec 文件

```bash
pyinstaller SherrySprite.spec
```

### 方法 3：手动打包

```bash
pyinstaller src/main.py \
    --name SherrySprite \
    --onedir \
    --windowed \
    --icon src/assets/hanamaru_icon.ico \
    --add-data "src/assets;src/assets" \
    --hidden-import PyQt6.sip \
    --hidden-import live2d.v3 \
    --hidden-import edge_tts \
    --hidden-import aiohttp \
    --hidden-import websockets \
    --clean
```

## 图标说明

打包使用 **花丸.png** 作为程序图标：

- 源文件：`src/assets/models/hanamaru/花丸.png`
- 图标文件：`src/assets/hanamaru_icon.ico`
- 打包时自动将 PNG 转换为 ICO 格式

如果需要更换图标：
1. 替换 `src/assets/models/hanamaru/花丸.png`
2. 删除 `src/assets/hanamaru_icon.ico`
3. 重新运行 `python build_exe.py`

## 打包前检查清单

- [ ] Python 3.9+ 已安装
- [ ] 所有依赖已安装：`pip install -r requirements.txt`
- [ ] PyInstaller 已安装：`pip install pyinstaller`
- [ ] Pillow 已安装（用于图标转换）：`pip install Pillow`
- [ ] 项目可以正常运行：`python src/main.py`

## 依赖安装

```bash
# 安装项目依赖
pip install -r requirements.txt

# 安装打包工具
pip install pyinstaller Pillow
```

## 输出文件

打包成功后，`dist/SherrySprite/` 目录包含：

```
SherrySprite/
├── SherrySprite.exe      # 主程序
├── 启动雪莉.bat          # 启动脚本
├── 使用说明.txt          # 使用说明
├── src/
│   └── assets/           # 资源文件
└── ...                   # 其他依赖文件
```

## 分发方式

### 方式 1：压缩包

将整个 `SherrySprite` 文件夹压缩为 zip/rar，用户解压后双击运行。

### 方式 2：安装程序

使用 Inno Setup 或 NSIS 创建安装程序。

### 方式 3：单文件模式

如需单文件（启动较慢）：

```bash
python build_exe.py --onefile
```

## 常见问题

### Q: 打包后运行报错 "找不到模块"

A: 检查 `build_exe.py` 中的 `hiddenimports` 列表，添加缺失的模块。

### Q: 图标不显示

A: 
1. 确保图标是有效的 ICO 文件
2. 清除缓存后重新打包：`python build_exe.py --clean`

### Q: Live2D 模型加载失败

A: 检查是否包含 shader 文件：
```python
# 在 build_exe.py 中检查
shader_path = get_live2d_shaders_path()
print(f"Shader path: {shader_path}")
```

### Q: 文件太大

A: 使用 UPX 压缩（自动启用），或在 spec 文件中添加排除：
```python
excludes=['matplotlib', 'numpy.random']
```

### Q: 杀毒软件报毒

A: 这是 PyInstaller 的常见问题，可以：
1. 将程序添加到杀毒软件白名单
2. 使用 `--onefile` 模式（某些杀毒软件对单文件模式更友好）
3. 购买代码签名证书

## 高级配置

### 修改打包脚本

编辑 `build_exe.py`，修改以下选项：

```python
# 输出名称
"--name", "SherrySprite",

# 图标路径
"--icon", str(icon_ico),

# 添加额外数据文件
"--add-data", "extra_folder;dest_folder",

# 添加隐藏导入
"--hidden-import", "module_name",
```

### 使用 UPX 压缩

下载 UPX 并添加到 PATH，PyInstaller 会自动使用。

## 参考

- [PyInstaller 文档](https://pyinstaller.readthedocs.io/)
- [Windows 图标格式](https://docs.microsoft.com/en-us/windows/win32/uxguide/vis-icons)
