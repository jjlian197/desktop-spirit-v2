#!/usr/bin/env python3
"""
🎀 Sherry Desktop Sprite Launcher
打包后的应用启动器 - 健壮版
"""

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
    
    SSH_HOST = "pc"
    PORT = 9880
    
    def __init__(self):
        self.ready = False
        self.error = None
        self.ssh_pid = None
        self._started = False
    
    def _check_ssh_available(self) -> bool:
        """检查 SSH 命令是否可用"""
        try:
            result = subprocess.run(["ssh", "-V"], capture_output=True, timeout=3)
            return result.returncode == 0 or b"OpenSSH" in result.stderr
        except:
            return False
    
    def _check_port(self, timeout=2) -> bool:
        """检测端口"""
        try:
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex(('127.0.0.1', self.PORT))
            sock.close()
            return result == 0
        except:
            return False
    
    def _setup_ssh(self) -> bool:
        """建立 SSH 隧道"""
        # 先检查 SSH 是否可用
        if not self._check_ssh_available():
            logger.warning("⚠️ SSH 命令不可用，跳过隧道建立")
            logger.warning("   请手动建立隧道: ssh -N -L 9880:127.0.0.1:9880 pc")
            return False
        
        try:
            if self._check_port():
                logger.info("🔌 SSH 隧道已存在")
                return True
            
            logger.info("🔌 建立 SSH 隧道...")
            cmd = ["ssh", "-N", "-L", f"{self.PORT}:127.0.0.1:{self.PORT}", self.SSH_HOST]
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                start_new_session=True
            )
            self.ssh_pid = proc.pid
            
            # 等待
            for _ in range(10):
                time.sleep(1)
                if self._check_port():
                    logger.info("✅ SSH 隧道已建立")
                    return True
            
            # 检查 stderr
            err = proc.stderr.read1(1024).decode('utf-8', errors='ignore') if hasattr(proc.stderr, 'read1') else ""
            if err:
                logger.warning(f"SSH 错误: {err[:100]}")
            
            logger.warning("⚠️ SSH 隧道建立失败")
            return False
            
        except Exception as e:
            logger.warning(f"SSH 错误: {e}")
            return False
    
    def _check_service(self) -> bool:
        """检查服务"""
        try:
            import urllib.request
            urllib.request.urlopen(f"http://127.0.0.1:{self.PORT}", timeout=2)
            return True
        except:
            return False
    
    def setup_env(self):
        """设置环境变量"""
        os.environ["GPT_SOVITS_URL"] = f"http://127.0.0.1:{self.PORT}/tts"
        os.environ["GPT_SOVITS_LANG"] = "zh"
        os.environ["GPT_SOVITS_REFER_WAV"] = (
            "D:/Workspace/1761703720454-qatfwm-sakiko1-e15/"
            "参考/なんだか申し訳ありませんわそれにしても可愛らしいお部屋ですわね.wav"
        )
        os.environ["GPT_SOVITS_PROMPT_TEXT"] = (
            "なんだか申し訳ありませんわそれにしても可愛らしいお部屋ですわね"
        )
        os.environ["GPT_SOVITS_PROMPT_LANG"] = "ja"
        os.environ["GPT_SOVITS_SPLIT_METHOD"] = "cut5"
        os.environ["GPT_SOVITS_SPEED"] = "1.0"
    
    def initialize(self):
        """初始化（在后台线程中运行）"""
        if self._started:
            return
        self._started = True
        
        try:
            logger.info("🎙️ 初始化 GPT-SoVITS...")
            
            # 尝试建立 SSH 隧道（失败不阻断）
            ssh_ok = self._setup_ssh()
            
            # 检测服务
            if self._check_service():
                logger.info("✅ GPT-SoVITS 服务可访问")
            else:
                if ssh_ok:
                    logger.warning("⚠️ GPT-SoVITS 未运行")
                    logger.info("   请手动在服务器上启动:")
                    logger.info("   python api_v2.py -a 127.0.0.1 -p 9880")
                else:
                    logger.warning("⚠️ 无法连接 GPT-SoVITS")
                    logger.info("   请确保:")
                    logger.info("   1. 手动建立 SSH 隧道")
                    logger.info("   2. GPT-SoVITS 已启动")
            
            # 无论如何都设置环境变量
            self.setup_env()
            self.ready = True
            logger.info("🎙️ GPT-SoVITS 配置完成")
            
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
