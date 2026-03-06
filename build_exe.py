#!/usr/bin/env python3
"""
PyInstaller 打包脚本 for Sherry Desktop Sprite (Windows)
使用方法: python build_exe.py
"""

import sys
import os
from pathlib import Path
import subprocess
import site


def get_live2d_shaders_path():
    """找到 live2d shader 文件的路径"""
    for site_dir in site.getsitepackages():
        shader_path = Path(site_dir) / "live2d" / "v3" / "FrameworkShaders"
        if shader_path.exists():
            return str(shader_path)
    # 备选：使用 pip show 找到包位置
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "show", "live2d-py"],
            capture_output=True, text=True
        )
        for line in result.stdout.split('\n'):
            if line.startswith('Location:'):
                location = line.split(':', 1)[1].strip()
                shader_path = Path(location) / "live2d" / "v3" / "FrameworkShaders"
                if shader_path.exists():
                    return str(shader_path)
    except:
        pass
    return None


def main():
    """Build executable using PyInstaller"""
    
    # 项目根目录
    project_dir = Path(__file__).parent.absolute()
    src_dir = project_dir / "src"
    
    print(f"[PACK] Project: {project_dir}")
    print(f"[PACK] Source: {src_dir}")
    
    # 检查 PyInstaller 是否安装
    try:
        import PyInstaller
        print(f"[OK] PyInstaller: {PyInstaller.__version__}")
    except ImportError:
        print("[INSTALL] PyInstaller...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], check=True)
        print("[OK] PyInstaller installed")
    
    # 找到 Live2D shader 路径
    shader_path = get_live2d_shaders_path()
    if shader_path:
        print(f"[OK] Live2D shaders: {shader_path}")
    else:
        print("[WARN] Live2D shaders not found!")
    
    # 构建 PyInstaller 命令
    cmd = [
        sys.executable, "-m", "PyInstaller",
        # 主入口文件
        str(src_dir / "main.py"),
        # 输出名称
        "--name", "SherrySprite",
        # 单目录模式
        "--onedir",
        # 窗口应用程序 (无控制台)
        "--windowed",
        # 清理缓存
        "--clean",
        # 覆盖现有输出
        "--noconfirm",
        # 工作目录
        "--workpath", str(project_dir / "build"),
        # 输出目录 (使用新目录避免冲突)
        "--distpath", str(project_dir / "dist_new"),
        # 图标
        "--icon", str(src_dir / "assets" / "icon.ico"),
        # 添加数据文件 (模型、资源等)
        "--add-data", f"{src_dir / 'assets'};src/assets",
        # 隐藏导入
        "--hidden-import", "PyQt6.sip",
        "--hidden-import", "PyQt6.QtCore",
        "--hidden-import", "PyQt6.QtGui",
        "--hidden-import", "PyQt6.QtWidgets",
        "--hidden-import", "PyQt6.QtOpenGL",
        "--hidden-import", "PyQt6.QtOpenGLWidgets",
        "--hidden-import", "live2d.v3",
        "--hidden-import", "live2d",
        "--hidden-import", "edge_tts",
        "--hidden-import", "pydub",
        "--hidden-import", "pygame",
        "--hidden-import", "aiohttp",
        "--hidden-import", "websockets",
        "--hidden-import", "websockets.legacy",
        "--hidden-import", "psutil",
        "--hidden-import", "loguru",
        "--hidden-import", "PIL",
        # 收集所有二进制文件
        "--collect-all", "live2d",
        "--collect-all", "PyQt6",
        # 包含 VC++ Runtime (避免目标电脑缺少)
        "--add-binary", r"C:\Windows\System32\msvcp140.dll;.",
        "--add-binary", r"C:\Windows\System32\vcruntime140.dll;.",
        "--add-binary", r"C:\Windows\System32\vcruntime140_1.dll;.",
    ]
    
    # 添加 Live2D shader 文件 (如果找到)
    if shader_path:
        cmd.extend(["--add-data", f"{shader_path};live2d/v3/FrameworkShaders"])
    
    print("\n[CMD] Building...")
    
    # 执行 PyInstaller
    result = subprocess.run(cmd, cwd=project_dir)
    
    if result.returncode == 0:
        print("\n[OK] Build successful!")
        print(f"[OUT] {project_dir / 'dist_new' / 'SherrySprite' / 'SherrySprite.exe'}")
        
        # 创建启动批处理文件
        bat_file = project_dir / "dist_new" / "SherrySprite" / "start.bat"
        with open(bat_file, 'w', encoding='utf-8') as f:
            f.write('@echo off\n')
            f.write('chcp 65001 >nul\n')
            f.write('title Sherry Desktop Sprite\n')
            f.write('echo Starting Sherry...\n')
            f.write('start "" "SherrySprite.exe"\n')
        print(f"[OUT] {bat_file}")
    else:
        print(f"\n[FAIL] Build failed: {result.returncode}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
