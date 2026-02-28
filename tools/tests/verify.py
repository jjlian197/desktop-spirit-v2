#!/usr/bin/env python3
"""
Sherry Desktop Sprite - Quick Verification Script
Checks that all dependencies are installed and configuration is valid
"""

import sys
from pathlib import Path

def check_python_version():
    """Check Python version"""
    version = sys.version_info
    if version.major == 3 and version.minor >= 9:
        print(f"✅ Python {version.major}.{version.minor}.{version.micro}")
        return True
    else:
        print(f"❌ Python {version.major}.{version.minor} (need 3.9+)")
        return False

def check_module(module_name, package_name=None):
    """Check if a module is installed"""
    try:
        __import__(module_name)
        print(f"✅ {package_name or module_name}")
        return True
    except ImportError:
        print(f"❌ {package_name or module_name} (not installed)")
        return False

def check_file(path, description):
    """Check if a file exists"""
    if Path(path).exists():
        print(f"✅ {description}")
        return True
    else:
        print(f"❌ {description} (not found)")
        return False

def main():
    print("🐱💜 Sherry Desktop Sprite - Verification")
    print("=" * 40)
    print()
    
    results = []
    
    # Check Python version
    print("Python Environment:")
    results.append(check_python_version())
    print()
    
    # Check required modules
    print("Required Modules:")
    results.append(check_module("PyQt6"))
    results.append(check_module("websockets"))
    results.append(check_module("loguru"))
    results.append(check_module("yaml", "pyyaml"))
    results.append(check_module("psutil"))
    results.append(check_module("live2d", "live2d-py (optional)"))
    print()
    
    # Check project files
    print("Project Files:")
    base = Path("/Users/mylianjie/.openclaw/workspace/projects/sherry-desktop-sprite")
    results.append(check_file(base / "src/main.py", "main.py"))
    results.append(check_file(base / "src/app.py", "app.py"))
    results.append(check_file(base / "src/core/sprite_window.py", "sprite_window.py"))
    results.append(check_file(base / "src/core/websocket_server.py", "websocket_server.py"))
    results.append(check_file(base / "config.yaml", "config.yaml"))
    results.append(check_file(base / "requirements.txt", "requirements.txt"))
    print()
    
    # Check scripts
    print("Scripts:")
    results.append(check_file(base / "scripts/install.sh", "install.sh"))
    results.append(check_file(base / "scripts/uninstall.sh", "uninstall.sh"))
    results.append(check_file(base / "launchd/com.sherry.sprite.plist", "launchd plist"))
    print()
    
    # Summary
    passed = sum(results)
    total = len(results)
    
    print("=" * 40)
    print(f"Results: {passed}/{total} checks passed")
    
    if passed == total:
        print()
        print("🎉 All checks passed! Sherry is ready to run!")
        print()
        print("Quick start:")
        print("  python3 src/main.py")
        print()
        print("Or install as service:")
        print("  ./scripts/install.sh")
        return 0
    else:
        print()
        print("⚠️  Some checks failed. Please install missing dependencies:")
        print("  pip3 install -r requirements.txt")
        return 1

if __name__ == "__main__":
    sys.exit(main())
