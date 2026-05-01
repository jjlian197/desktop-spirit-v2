#!/usr/bin/env python3
"""
Sherry Desktop Sprite - Main Application
🐱💜 A cute desktop pet powered by Live2D and PyQt6
"""

import sys
import os
import asyncio
import signal
from pathlib import Path

# QWebEngine starts a Chromium helper process for the VRM renderer. These flags
# keep it usable in locked-down Windows launch contexts and CI smoke tests.
os.environ.setdefault("QTWEBENGINE_DISABLE_SANDBOX", "1")
os.environ.setdefault("QTWEBENGINE_CHROMIUM_FLAGS", "--no-sandbox --disable-gpu")

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from loguru import logger

from src.core.sprite_window import SherrySpriteWindow
from src.core.websocket_server import WebSocketServer
from src.core.http_server import HTTPServer
from src.utils.logger import setup_logging
from src.core.lip_sync_websocket import LipSyncWebSocketBroadcaster
from src.brain.sprite_brain import SpriteBrain
from PyQt6.QtCore import QThread


class BrainThread(QThread):
    """在独立线程中运行大脑"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.brain = None
        
    def run(self):
        """线程入口"""
        import asyncio
        self.brain = SpriteBrain()
        try:
            asyncio.run(self.brain.start())
        except Exception as e:
            from loguru import logger
            logger.error(f"Brain error: {e}")
    
    def stop(self):
        """停止大脑"""
        if self.brain:
            self.brain.stop()

def setup_signal_handlers(app):
    """Setup graceful shutdown handlers"""
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, shutting down gracefully...")
        app.quit()
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)


class SherryApplication(QApplication):
    """Main Application with exception handling"""
    
    def __init__(self, argv):
        # Enable high DPI scaling BEFORE calling super().__init__
        QApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
        )
        
        super().__init__(argv)
        
        # 设置应用程序图标（Windows 任务栏需要）
        self._setup_icon()
        
        # Global exception handler
        sys.excepthook = self.handle_exception
        
        # Create required directories
        self._ensure_directories()
    
    def _setup_icon(self):
        """设置应用程序图标"""
        try:
            from PyQt6.QtGui import QIcon
            from pathlib import Path
            import sys
            
            # 获取图标路径
            if hasattr(sys, '_MEIPASS'):
                icon_path = Path(sys._MEIPASS) / "src" / "assets" / "icon.ico"
            else:
                icon_path = Path(__file__).parent / "assets" / "icon.ico"
            
            if icon_path.exists():
                self.setWindowIcon(QIcon(str(icon_path)))
                logger.info(f"[ICON] Application icon set: {icon_path}")
            else:
                logger.warning(f"[ICON] Icon not found: {icon_path}")
        except Exception as e:
            logger.warning(f"[ICON] Failed to set icon: {e}")
    
    def _ensure_directories(self):
        """Create required directories"""
        home = Path.home()
        sherry_dir = home / '.sherry'
        sherry_dir.mkdir(exist_ok=True)
    
    def handle_exception(self, exc_type, exc_value, exc_traceback):
        """Handle uncaught exceptions"""
        import traceback
        error_msg = ''.join(traceback.format_exception(exc_type, exc_value, exc_traceback))
        logger.critical(f"Uncaught exception:\n{error_msg}")
        
        # Exit with error to trigger launchd restart
        sys.exit(1)


def main():
    """Main entry point"""
    # Setup logging
    setup_logging()
    
    logger.info("🐱💜 Starting Sherry Desktop Sprite...")
    
    # Create Qt Application
    app = SherryApplication(sys.argv)
    
    # Setup signal handlers
    setup_signal_handlers(app)
    
    # Create main window
    window = SherrySpriteWindow()
    window.show()
    
    # Start WebSocket server in background
    ws_server = WebSocketServer(window)
    ws_server.start()
    
    # Start HTTP API server in background
    import threading
    import asyncio
    http_server = HTTPServer(window, host="127.0.0.1", port=8766)
    
    def run_http_server():
        """Run HTTP server in background thread"""
        asyncio.run(http_server.start())
    
    http_thread = threading.Thread(target=run_http_server, daemon=True)
    http_thread.start()
    
    # 🚨 【触觉反馈】连接触摸事件到 WebSocket 广播
    def on_touch_event(action, part):
        """当雪莉被触摸时，广播到大脑（线程安全）"""
        from loguru import logger
        logger.info(f"🔄 转发触摸事件: {action} on {part}")
        # 使用线程安全的广播方法
        ws_server.broadcast_sync("touch_event", {
            "action": action,
            "part": part
        })
    
    window.touch_event.connect(on_touch_event)
    
    logger.info("✅ Sherry Desktop Sprite started successfully!")
    logger.info("   WebSocket: ws://127.0.0.1:8765/sprite")
    logger.info("   HTTP API: http://127.0.0.1:8766")
    
    # Start Brain thread (精灵大脑)
    brain_thread = BrainThread()
    brain_thread.start()
    logger.info("🧠 大脑已启动 (鼠标跟随激活)")
    
    # Run Qt event loop
    exit_code = app.exec()
    
    # Cleanup
    ws_server.stop()
    brain_thread.stop()
    brain_thread.wait(2000)  # 等待2秒让大脑优雅退出
    logger.info("👋 Sherry Desktop Sprite stopped.")
    
    return exit_code


if __name__ == '__main__':
    sys.exit(main())
