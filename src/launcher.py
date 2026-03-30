#!/usr/bin/env python3
"""
🎀 Sherry Desktop Sprite Launcher
打包后的应用启动器 - 健壮版
"""

import multiprocessing
# 🚨 PyInstaller 多进程支持：必须在其他导入之前调用
multiprocessing.freeze_support()

import os
import sys
import time
import subprocess
import threading
from pathlib import Path

# 配置日志
from loguru import logger

logger.remove()
logger.add(
    lambda msg: print(msg, end=""),
    colorize=True,
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
    level="INFO"
)


class GPTSoVITSManager:
    """GPT-SoVITS 管理器"""

    def __init__(self):
        self.ready = False
        self.error = None
        self._started = False

    def setup_env(self):
        """设置环境变量（子类可重写）"""
        pass
    
    def initialize(self):
        """初始化（在后台线程中运行）"""
        if self._started:
            return
        self._started = True

        try:
            logger.info("🎙️ 初始化 GPT-SoVITS...")

            # 🚀 SSH 隧道已禁用 - 如果需要远程 GPT-SoVITS，请手动建立隧道
            # ssh -N -L 9880:127.0.0.1:9880 pc

            # 设置环境变量
            self.setup_env()
            self.ready = True
            logger.info("🎙️ GPT-SoVITS 配置完成（SSH 隧道已禁用）")

        except Exception as e:
            logger.error(f"初始化错误: {e}")
            # 即使出错也设置环境变量，让应用能启动
            self.setup_env()
    
    def start_async(self):
        """后台启动"""
        thread = threading.Thread(target=self.initialize, daemon=True)
        thread.start()
        return thread


# 全局实例
_gptsovits_mgr = None


def main():
    """主入口"""
    global _gptsovits_mgr
    
    # 处理打包路径
    if getattr(sys, 'frozen', False):
        bundle_dir = sys._MEIPASS
        os.chdir(bundle_dir)
    else:
        project_root = Path(__file__).parent.parent
        os.chdir(project_root)
        sys.path.insert(0, str(project_root))
    
    print("\n" + "="*50)
    print(" 🎀 Sherry Desktop Sprite")
    print("="*50 + "\n")
    
    # 🚨 检查是否需要跳过 launcher（环境变量控制）
    if os.environ.get("SHERRY_NO_LAUNCHER") == "1":
        logger.info("🚀 使用原始启动模式（跳过 GPT-SoVITS 初始化）")
        from src.app import main as sherry_main
        return sherry_main()
    
    # 创建并启动 GPT-SoVITS 管理器（后台）
    _gptsovits_mgr = GPTSoVITSManager()
    _gptsovits_mgr.start_async()
    
    # 给后台线程一点时间，但不等待
    time.sleep(0.5)
    
    try:
        # 启动主应用
        from src.app import main as sherry_main
        return sherry_main()
    except Exception as e:
        logger.error(f"启动失败: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
