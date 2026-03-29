# -*- mode: python ; coding: utf-8 -*-
# 🐛 调试版本 - 显示控制台输出，便于排查问题

import os
import sys

venv_path = os.path.dirname(sys.executable)
python_version = f'{sys.version_info.major}.{sys.version_info.minor}'
live2d_shaders = os.path.join(
    venv_path, '..', 'lib', f'python{python_version}', 'site-packages', 
    'live2d', 'v3', 'FrameworkShaders'
)
live2d_shaders = os.path.normpath(live2d_shaders)

a = Analysis(
    ['src/launcher.py'],
    pathex=[],
    binaries=[
        (os.path.join(venv_path, 'edge-tts'), '.'),
    ],
    datas=[
        ('src/assets/models', 'src/assets/models'),
        ('config.yaml', '.'),
        (live2d_shaders, 'live2d/v3/FrameworkShaders'),
    ],
    hiddenimports=[
        'urllib.request',
        'socket',
        'threading',
        'subprocess',
        'edge_tts',
        'edge_tts.constants',
        'edge_tts.exceptions',
        'websockets',
        'websockets.legacy',
        'websockets.legacy.server',
        'aiohttp',
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.QtWidgets',
        'PyQt6.QtOpenGL',
        'PyQt6.QtOpenGLWidgets',
        'OpenGL',
        'OpenGL.GL',
        'live2d',
        'live2d.v3',
        'numpy',
        'yaml',
        'loguru',
        'psutil',
        'objc',
        'AppKit',
        'Foundation',
        'Quartz',
        'HIServices',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=['src/core/_pyinstaller_hook.py'],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='SherryApp_debug',
    debug=True,  # 🐛 开启调试
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,  # 🐛 显示控制台（关键！）
    disable_windowed_traceback=False,
    argv_emulation=False,
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
    name='SherryApp_debug',
)
app = BUNDLE(
    coll,
    name='SherryApp_debug.app',
    icon='sherry.icns',
    bundle_identifier='com.sherry.sprite.debug',
)
