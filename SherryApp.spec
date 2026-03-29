# -*- mode: python ; coding: utf-8 -*-
import os
import sys

# 获取虚拟环境路径
venv_path = os.path.dirname(sys.executable)

# 获取 live2d 着色器路径（用于打包）
python_version = f'{sys.version_info.major}.{sys.version_info.minor}'
live2d_shaders = os.path.join(
    venv_path, '..', 'lib', f'python{python_version}', 'site-packages', 
    'live2d', 'v3', 'FrameworkShaders'
)
live2d_shaders = os.path.normpath(live2d_shaders)  # 规范化路径

a = Analysis(
    ['src/launcher.py'],  # 🎀 使用 launcher 作为入口点
    pathex=[],
    binaries=[
        # 打包 edge-tts 命令行工具
        (os.path.join(venv_path, 'edge-tts'), '.'),
    ],
    datas=[
        ('src/assets/models', 'src/assets/models'),  # 保持目录结构
        ('config.yaml', '.'),
        # Live2D 着色器文件（必须！）
        (live2d_shaders, 'live2d/v3/FrameworkShaders'),
    ],
    hiddenimports=[
        # 🎀 Launcher 依赖
        'urllib.request',
        'socket',
        'threading',
        'subprocess',
        # TTS 相关
        'edge_tts',
        'edge_tts.constants',
        'edge_tts.exceptions',
        # WebSocket / HTTP
        'websockets',
        'websockets.legacy',
        'websockets.legacy.server',
        'aiohttp',
        # PyQt6 组件
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.QtWidgets',
        'PyQt6.QtOpenGL',
        'PyQt6.QtOpenGLWidgets',
        # OpenGL
        'OpenGL',
        'OpenGL.GL',
        # Live2D
        'live2d',
        'live2d.v3',
        # STT 相关
        'faster_whisper',
        'pyaudio',
        'cffi',
        # 其他
        'numpy',
        'yaml',
        'loguru',
        'psutil',
        'objc',
        # macOS 特定
        'AppKit',
        'Foundation',
        'Quartz',
        'HIServices',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=['src/core/_pyinstaller_hook.py'],
    excludes=[],  # 不排除任何模块
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='SherryApp',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # 生产环境设为 False
    disable_windowed_traceback=False,
    argv_emulation=False,  # macOS app bundle 建议设为 False
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['sherry.icns'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='SherryApp',
)
app = BUNDLE(
    coll,
    name='SherryApp.app',
    icon='sherry.icns',
    bundle_identifier='com.sherry.sprite',
)
