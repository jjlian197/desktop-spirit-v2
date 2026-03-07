#!/usr/bin/env python3
"""
PyInstaller 打包脚本 for Sherry Desktop Sprite (Windows)
使用方法: python build_exe.py
图标: 使用花丸.png 作为程序图标
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
    assets_dir = src_dir / "assets"
    
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
    
    # 检查 PIL 是否安装（用于图标转换）
    try:
        from PIL import Image
        print("[OK] PIL available for icon conversion")
    except ImportError:
        print("[INSTALL] Pillow...")
        subprocess.run([sys.executable, "-m", "pip", "install", "Pillow"], check=True)
        print("[OK] Pillow installed")
    
    # 准备图标：使用花丸.png
    icon_png = assets_dir / "models" / "hanamaru" / "花丸.png"
    icon_ico = assets_dir / "hanamaru_icon.ico"
    
    # 如果图标不存在，创建它
    if not icon_ico.exists() and icon_png.exists():
        print(f"[ICON] Converting 花丸.png to ICO...")
        try:
            from PIL import Image
            img = Image.open(icon_png).convert('RGBA')
            sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
            img.save(icon_ico, format='ICO', sizes=sizes)
            print(f"[OK] Created icon: {icon_ico}")
        except Exception as e:
            print(f"[WARN] Failed to create icon: {e}")
            icon_ico = assets_dir / "icon.ico"  # 使用备选图标
    
    if not icon_ico.exists():
        print(f"[WARN] Icon not found: {icon_ico}")
        icon_ico = assets_dir / "icon.ico"
    
    print(f"[ICON] Using: {icon_ico}")
    
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
        # 单目录模式（启动更快，适合大型应用）
        "--onedir",
        # 窗口应用程序 (无控制台)
        "--windowed",
        # 清理缓存
        "--clean",
        # 覆盖现有输出
        "--noconfirm",
        # 工作目录
        "--workpath", str(project_dir / "build"),
        # 输出目录
        "--distpath", str(project_dir / "dist"),
        # 图标（使用花丸图标）
        "--icon", str(icon_ico),
        # 添加数据文件 (模型、资源等)
        "--add-data", f"{assets_dir};src/assets",
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
        "--hidden-import", "yaml",
        # 收集所有二进制文件
        "--collect-all", "live2d",
        "--collect-all", "PyQt6",
    ]
    
    # 添加 VC++ Runtime (如果存在)
    vc_dlls = [
        r"C:\Windows\System32\msvcp140.dll",
        r"C:\Windows\System32\vcruntime140.dll",
        r"C:\Windows\System32\vcruntime140_1.dll",
    ]
    for dll in vc_dlls:
        if os.path.exists(dll):
            cmd.extend(["--add-binary", f"{dll};."])
    
    # 添加 Live2D shader 文件 (如果找到)
    if shader_path:
        cmd.extend(["--add-data", f"{shader_path};live2d/v3/FrameworkShaders"])
    
    print("\n[CMD] Building with PyInstaller...")
    print("This may take a few minutes...")
    
    # 执行 PyInstaller
    result = subprocess.run(cmd, cwd=project_dir)
    
    if result.returncode == 0:
        print("\n" + "="*60)
        print("[OK] Build successful!")
        print("="*60)
        
        exe_path = project_dir / "dist" / "SherrySprite" / "SherrySprite.exe"
        print(f"[OUT] Executable: {exe_path}")
        
        # 创建启动批处理文件
        bat_file = project_dir / "dist" / "SherrySprite" / "启动雪莉.bat"
        with open(bat_file, 'w', encoding='utf-8') as f:
            f.write('@echo off\n')
            f.write('chcp 65001 >nul\n')
            f.write('title Sherry Desktop Sprite\n')
            f.write('echo Starting Sherry...\n')
            f.write('echo 正在启动雪莉...\n')
            f.write('start "" "SherrySprite.exe"\n')
        print(f"[OUT] Launcher: {bat_file}")
        
        # 创建说明文件
        readme_file = project_dir / "dist" / "SherrySprite" / "使用说明.txt"
        with open(readme_file, 'w', encoding='utf-8') as f:
            f.write("Sherry Desktop Sprite - 雪莉桌面精灵\n")
            f.write("="*50 + "\n\n")
            f.write("启动方式:\n")
            f.write("1. 双击 SherrySprite.exe 启动\n")
            f.write("2. 或双击 启动雪莉.bat 启动\n\n")
            f.write("使用方法:\n")
            f.write("- 右键点击雪莉打开菜单\n")
            f.write("- 左键拖动移动位置\n")
            f.write("- 在菜单中可以切换语言(中/日/英)\n\n")
            f.write("配置文件:\n")
            f.write("- 编辑 config.yaml 配置翻译API\n\n")
        print(f"[OUT] Readme: {readme_file}")
        
        print("\n" + "="*60)
        print("打包完成！输出目录: dist/SherrySprite/")
        print("="*60)
    else:
        print(f"\n[FAIL] Build failed with code: {result.returncode}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
