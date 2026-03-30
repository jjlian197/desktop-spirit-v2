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

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt, QThread
from loguru import logger

from src.core.sprite_window import SherrySpriteWindow
from src.core.websocket_server import WebSocketServer
from src.utils.logger import setup_logging
from src.core.lip_sync_websocket import LipSyncWebSocketBroadcaster
from src.brain.sprite_brain import SpriteBrain


class BrainThread(QThread):
    """在独立线程中运行大脑"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.brain = None
        
    def run(self):
        """线程入口"""
        self.brain = SpriteBrain()
        try:
            asyncio.run(self.brain.start())
        except Exception as e:
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
        super().__init__(argv)
        
        # Global exception handler
        sys.excepthook = self.handle_exception
        
        # Enable high DPI scaling
        self.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
        )
        
        # Create required directories
        self._ensure_directories()
    
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
    
    # 🚨 【触觉反馈】连接触摸事件到 WebSocket 广播
    def on_touch_event(action, part):
        """当雪莉被触摸时，广播到大脑（线程安全）"""
        logger.info(f"🔄 转发触摸事件: {action} on {part}")
        # 使用线程安全的广播方法
        ws_server.broadcast_sync("touch_event", {
            "action": action,
            "part": part
        })
    
    window.touch_event.connect(on_touch_event)
    
    logger.info("✅ Sherry Desktop Sprite started successfully!")
    logger.info("   WebSocket: ws://127.0.0.1:8765/sprite")
    
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
