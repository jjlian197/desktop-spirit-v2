# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas = [('C:\\Users\\lianj\\Python\\desktop-spirit-v2-windows\\src\\assets', 'src/assets'), ('C:\\Users\\lianj\\AppData\\Local\\Programs\\Python\\Python311\\Lib\\site-packages\\live2d\\v3\\FrameworkShaders', 'live2d/v3/FrameworkShaders')]
binaries = [('C:\\Windows\\System32\\msvcp140.dll', '.'), ('C:\\Windows\\System32\\vcruntime140.dll', '.'), ('C:\\Windows\\System32\\vcruntime140_1.dll', '.')]
hiddenimports = ['PyQt6.sip', 'PyQt6.QtCore', 'PyQt6.QtGui', 'PyQt6.QtWidgets', 'PyQt6.QtOpenGL', 'PyQt6.QtOpenGLWidgets', 'live2d.v3', 'live2d', 'edge_tts', 'pydub', 'pygame', 'aiohttp', 'websockets', 'websockets.legacy', 'psutil', 'loguru', 'PIL', 'yaml']
tmp_ret = collect_all('live2d')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('PyQt6')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]


a = Analysis(
    ['C:\\Users\\lianj\\Python\\desktop-spirit-v2-windows\\src\\main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
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
    name='SherrySprite',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['C:\\Users\\lianj\\Python\\desktop-spirit-v2-windows\\src\\assets\\hanamaru_icon.ico'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='SherrySprite',
)
