# Utility functions
"""
通用工具函数
"""
import os
import sys
from pathlib import Path


def get_resource_path(relative_path: str) -> str:
    """
    获取资源文件的正确路径
    
    在开发环境中：相对于项目根目录
    在 PyInstaller 打包后：相对于临时解压目录 _MEIPASS
    
    Args:
        relative_path: 相对于项目根目录的资源路径 (如 "src/assets/models/hanamaru")
        
    Returns:
        str: 资源的绝对路径
    """
    # PyInstaller 会在运行时解压资源到 sys._MEIPASS
    if hasattr(sys, '_MEIPASS'):
        # 打包后的环境
        base_path = Path(sys._MEIPASS)
    else:
        # 开发环境：从当前文件向上找到项目根目录
        # 当前文件: src/utils/__init__.py
        # 项目根目录: src/utils/__init__.py -> src/utils -> src -> 项目根目录
        current_file = Path(__file__).resolve()
        base_path = current_file.parent.parent.parent
    
    return str(base_path / relative_path)


def get_project_root() -> Path:
    """
    获取项目根目录
    
    Returns:
        Path: 项目根目录路径
    """
    if hasattr(sys, '_MEIPASS'):
        return Path(sys._MEIPASS)
    else:
        current_file = Path(__file__).resolve()
        return current_file.parent.parent.parent
