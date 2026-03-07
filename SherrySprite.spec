# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for Sherry Desktop Sprite
图标使用花丸.png
"""

import sys
from pathlib import Path

# 项目路径
project_dir = Path(SPECFILE).parent
src_dir = project_dir / "src"
assets_dir = src_dir / "assets"

# 图标路径（使用花丸图标）
icon_path = assets_dir / "hanamaru_icon.ico"
if not icon_path.exists():
    icon_path = assets_dir / "icon.ico"

block_cipher = None

a = Analysis(
    [str(src_dir / 'main.py')],
    pathex=[str(project_dir)],
    binaries=[],
    datas=[
        (str(assets_dir), 'src/assets'),
    ],
    hiddenimports=[
        'PyQt6.sip',
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.QtWidgets',
        'PyQt6.QtOpenGL',
        'PyQt6.QtOpenGLWidgets',
        'live2d.v3',
        'live2d',
        'edge_tts',
        'pydub',
        'pygame',
        'aiohttp',
        'websockets',
        'websockets.legacy',
        'psutil',
        'loguru',
        'PIL',
        'yaml',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='SherrySprite',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(icon_path),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='SherrySprite',
)
