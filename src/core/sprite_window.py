#!/usr/bin/env python3
"""
Sherry Sprite Window - Transparent, Frameless, Always-on-Top
"""

import sys
import platform
from pathlib import Path

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout,
    QApplication, QSystemTrayIcon, QMenu
)
from PyQt6.QtCore import Qt, QPoint, QTimer, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QIcon, QAction, QFont
from loguru import logger

from src.ui.bubble_widget import BubbleWidget
try:
    from src.core.live2d_view import Live2DView, HAS_LIVE2D
except ImportError:
    HAS_LIVE2D = False

# Import resource path utility
try:
    from src.utils import get_resource_path
except ImportError:
    # Fallback if utils not available
    def get_resource_path(relative_path: str) -> str:
        """简单的路径处理，仅适用于开发环境"""
        if hasattr(sys, '_MEIPASS'):
            return str(Path(sys._MEIPASS) / relative_path)
        return relative_path

# Import TTS Manager
try:
    from src.core.tts_manager import TTSManager, get_tts_manager
    HAS_TTS = True
except ImportError:
    HAS_TTS = False

# macOS Native Window Level Support
HAS_MACOS_LEVEL = False
if platform.system() == 'Darwin':
    try:
        import Cocoa
        import Quartz
        HAS_MACOS_LEVEL = True
    except ImportError:
        pass


class SherrySpriteWindow(QMainWindow):
    """Main window for Sherry Desktop Sprite"""

    # Signals for WebSocket communication
    expression_changed = pyqtSignal(str)
    motion_triggered = pyqtSignal(str, int)
    message_received = pyqtSignal(str, int)
    
    # ?? 【触觉反馈】触摸事件信号 - 当用户触摸雪莉时发射
    touch_event = pyqtSignal(str, str)  # (action, part) 例如 ("tap", "head")

    def __init__(self):
        super().__init__()

        self.drag_position = None
        self.bubble_widget = None
        self.is_click_through = False
        self.is_big_head = False
        self._watermark_enabled = False

        # Initialize TTS manager
        self.tts_manager = None
        if HAS_TTS:
            try:
                self.tts_manager = get_tts_manager()
                logger.info("? SpriteWindow: TTS manager initialized")
            except Exception as e:
                logger.error(f"Failed to initialize TTS manager: {e}")

        # Setup window properties
        self._setup_window()
        self._setup_ui()
        self._setup_tray()
        self._position_bottom_right()
        
        # 显示窗口并记录位置
        self.show()
        logger.info(f"[WINDOW] Position: ({self.x()}, {self.y()}), Size: ({self.width()}, {self.height()})")
        logger.info(f"[WINDOW] Visible: {self.isVisible()}, WindowState: {self.windowState()}")
        
        logger.info("Sprite window initialized")

    def _setup_window(self):
        # 使用标准置顶且不夺取焦点的标志
        self.setWindowFlags(
            Qt.WindowType.Window |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(400, 600)
        
        # 设置窗口图标（任务栏显示）
        icon_path = get_resource_path("src/assets/icon.ico")
        if Path(icon_path).exists():
            self.setWindowIcon(QIcon(icon_path))
            logger.info(f"[ICON] Window icon set: {icon_path}")
        else:
            logger.warning(f"[ICON] Window icon not found: {icon_path}")
       
        self.setStyleSheet("SherrySpriteWindow { background: transparent; }")
        
    def _setup_ui(self):
        # 创建主容器
        self.central_widget = QWidget()
        self.central_widget.setObjectName("centralWidget")
        self.setCentralWidget(self.central_widget)
        
        # 使用绝对定位布局
        from PyQt6.QtWidgets import QVBoxLayout
        layout = QVBoxLayout(self.central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # 创建 Live2D 视图
        self.live2d_view = None
        logger.info(f"?? HAS_LIVE2D = {HAS_LIVE2D}")
        if HAS_LIVE2D:
            try:
                logger.info("?? Creating Live2DView...")
                self.live2d_view = Live2DView(self.central_widget)
                self.live2d_view.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
                layout.addWidget(self.live2d_view)
                logger.info("? Live2DView created and added to layout")
                
                # Connect model loaded signal for auto watermark removal
                self.live2d_view.model_loaded.connect(self._auto_remove_watermark)
                # ?? 【触觉反馈】连接触摸信号到窗口级信号
                self.live2d_view.touched.connect(self._on_touched)
                
                # 加载模型 - 使用 get_resource_path 确保打包后路径正确
                model_path = get_resource_path("src/assets/models/hanamaru")
                logger.info(f"?? Loading model from: {model_path}")
                
                # 检查路径是否存在
                import os
                if os.path.exists(model_path):
                    logger.info(f"? Model path exists: {model_path}")
                    # 列出目录内容
                    try:
                        files = os.listdir(model_path)
                        logger.info(f"?? Files in model dir: {files}")
                    except Exception as e:
                        logger.warning(f"?? Cannot list model dir: {e}")
                else:
                    logger.error(f"? Model path does NOT exist: {model_path}")
                
                success = self.live2d_view.load_model(model_path)
                logger.info(f"?? Model load result: {success}")
                
            except Exception as e:
                logger.error(f"? Failed to initialize Live2D: {e}")
                import traceback
                logger.error(traceback.format_exc())
        else:
            logger.error("? HAS_LIVE2D is False, skipping Live2D initialization")

        self.bubble_widget = BubbleWidget(self)
        self.bubble_widget.hide()
        self.message_received.connect(self.show_message)

    def _setup_tray(self):
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return
        self.tray_icon = QSystemTrayIcon(self)
        
        # 设置托盘图标
        icon_path = get_resource_path("src/assets/icon.ico")
        if Path(icon_path).exists():
            self.tray_icon.setIcon(QIcon(icon_path))
            logger.info(f"[ICON] Tray icon set: {icon_path}")
        else:
            logger.warning(f"[ICON] Tray icon not found: {icon_path}")
        
        tray_menu = QMenu()
        
        show_action = QAction("Show Sherry", self)
        show_action.triggered.connect(self.show)
        tray_menu.addAction(show_action)
        
        tray_menu.addSeparator()
        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(QApplication.quit)
        tray_menu.addAction(quit_action)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()

    
    def set_click_through(self, enabled: bool):
        self.is_click_through = enabled
        
        # 1. 控件层级穿透：通知 Qt 内部的所有画板不要拦截鼠标
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, enabled)
        if self.central_widget:
            self.central_widget.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, enabled)
        if self.live2d_view:
            self.live2d_view.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, enabled)
            
        # 2. ?? 窗口层级穿透：使用 Qt 原生系统标志，它会自动调用 macOS 底层的忽略鼠标 API
        self.setWindowFlag(Qt.WindowType.WindowTransparentForInput, enabled)
        
        # 3. ?? 极其关键：在运行时修改 WindowFlag 会导致底层原生窗口被重置，必须调用 show() 将状态推送到系统！
        self.show()
        
        logger.info(f"??? Click-through {'enabled' if enabled else 'disabled'}")
        
    @pyqtSlot(str)
    def set_background(self, bg_type: str):
        """设置窗口背景 - 支持纯色、渐变、透明和本地图片路径"""
        logger.info(f"Background change requested: {bg_type} (not implemented)")
            
    def toggle_big_head_mode(self):
        self.is_big_head = not self.is_big_head
        if self.is_big_head:
            self.setFixedSize(400, 400)
        else:
            self.setFixedSize(400, 600)
        self._position_bottom_right()
        if self.live2d_view:
            self.live2d_view.set_big_head_mode(self.is_big_head)

    def _position_bottom_right(self):
        screen = QApplication.primaryScreen().geometry()
        x = screen.width() - self.width() - 20
        y = screen.height() - self.height() - 50
        self.move(x, y)

    def _show_context_menu(self, pos):
        menu = QMenu(self)

        # Expression menu (Param-based)
        expr_menu = menu.addMenu("Expression")
        expressions = [
            ("Normal", "normal"),
            ("Happy", "happy"),
            ("Sad", "sad"),
            ("Angry", "angry"),
            ("Love", "love"),
            ("Blush", "blush"),
            ("Daze", "daze"),
        ]
        for label, name in expressions:
            action = QAction(label, self)
            action.triggered.connect(lambda checked, n=name: self.set_expression(n))
            expr_menu.addAction(action)

        menu.addSeparator()
        
        # Watermark toggle
        watermark_action = QAction("去水印 (Toggle Watermark)", self)
        watermark_action.triggered.connect(self._toggle_watermark)
        menu.addAction(watermark_action)

        # Click-through toggle
        ct_action = QAction("??? 鼠标穿透 (Click Through)", self)
        ct_action.setCheckable(True)
        ct_action.setChecked(self.is_click_through)
        ct_action.triggered.connect(self.set_click_through)
        menu.addAction(ct_action)

        # Big head mode toggle
        bh_action = QAction("?? 大头模式 (Big Head Mode)", self)
        bh_action.setCheckable(True)
        bh_action.setChecked(self.is_big_head)
        bh_action.triggered.connect(self.toggle_big_head_mode)
        menu.addAction(bh_action)
        
        # Eye tracking toggle
        eye_action = QAction("??? 视线跟随 (Eye Tracking)", self)
        eye_action.setCheckable(True)
        eye_tracking_enabled = self.live2d_view and getattr(self.live2d_view, '_eye_tracking_enabled', True)
        eye_action.setChecked(eye_tracking_enabled)
        eye_action.triggered.connect(self._toggle_eye_tracking)
        menu.addAction(eye_action)

        menu.addSeparator()

        # ??? TTS Test Menu
        tts_menu = menu.addMenu("??? TTS 设置")

        # ?? TTS Master Switch
        tts_master_action = QAction("??? 启用语音 (TTS)", self)
        tts_master_action.setCheckable(True)
        # Get current TTS state from backend
        tts_enabled = self._get_tts_state()
        tts_master_action.setChecked(tts_enabled)
        tts_master_action.triggered.connect(self._toggle_tts_master)
        tts_menu.addAction(tts_master_action)

        tts_menu.addSeparator()

        # Provider selection submenu
        provider_menu = tts_menu.addMenu("选择引擎")
        if HAS_TTS and self.tts_manager:
            available = self.tts_manager.get_available_providers()
            for provider_name in available:
                action = QAction(provider_name.title(), self)
                is_current = self.tts_manager.current_provider.name.lower() == provider_name
                action.setCheckable(True)
                action.setChecked(is_current)
                action.triggered.connect(lambda checked, p=provider_name: self._switch_tts_provider(p))
                provider_menu.addAction(action)
        else:
            no_tts_action = QAction("TTS 不可用", self)
            no_tts_action.setEnabled(False)
            provider_menu.addAction(no_tts_action)

        tts_menu.addSeparator()

        # Test phrases
        test_phrases = [
            ("你好，世界！", "你好，世界！我是雪莉~"),
            ("测试语音", "这是一个语音测试，你能听到我说话吗？"),
            ("长句测试", "今天天气真不错，适合出去散步和喝咖啡呢！"),
            ("英文测试", "Hello, this is a test of the TTS system."),
        ]

        from functools import partial
        for label, phrase in test_phrases:
            action = QAction(label, self)
            action.triggered.connect(partial(self._test_tts, phrase))
            tts_menu.addAction(action)

        # Lip sync toggle
        if HAS_TTS and self.tts_manager:
            tts_menu.addSeparator()
            lip_sync_action = QAction("?? 口型同步", self)
            lip_sync_action.setCheckable(True)
            # Check if live2d_view has lip sync enabled
            lip_sync_enabled = True
            if self.live2d_view and hasattr(self.live2d_view, '_lip_sync_enabled'):
                lip_sync_enabled = self.live2d_view._lip_sync_enabled
            lip_sync_action.setChecked(lip_sync_enabled)
            lip_sync_action.triggered.connect(self._toggle_lip_sync)
            tts_menu.addAction(lip_sync_action)

        menu.addSeparator()
        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(QApplication.quit)
        menu.addAction(quit_action)

        menu.exec(pos)

    def _toggle_watermark(self):
        self._watermark_enabled = not self._watermark_enabled
        val = -1.0 if self._watermark_enabled else 0.0
        self.set_parameter("Open_EyeMask4", val)
    
    def _auto_remove_watermark(self):
        """启动时自动去水印"""
        self._watermark_enabled = True
        self.set_parameter("Open_EyeMask4", -1.0)
        logger.info("?? 已自动启用去水印")
    
    def _on_touched(self, action: str, part: str):
        """?? 【触觉反馈】处理触摸事件，转发到大脑"""
        logger.info(f"?? 雪莉感受到了主人的{action}，部位: {part}")
        # 发射信号，由 app.py 转发到 WebSocket
        self.touch_event.emit(action, part)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
        elif event.button() == Qt.MouseButton.RightButton:
            self._show_context_menu(event.globalPosition().toPoint())

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and self.drag_position:
            self.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()

    @pyqtSlot(str)
    def set_expression(self, name: str):
        if self.live2d_view:
            self.live2d_view.set_expression(name)

    @pyqtSlot(str, float)
    def set_parameter(self, param_id: str, value: float):
        if self.live2d_view:
            self.live2d_view.set_parameter(param_id, value)

    @pyqtSlot(float, float)
    def look_at(self, x: float, y: float):
        """设置眼神看向指定位置 (x, y 范围 -1.0 到 1.0)"""
        if self.live2d_view:
            self.live2d_view.mouse_x = x
            self.live2d_view.mouse_y = y
            self.live2d_view.update()
            logger.info(f"?? Look at: ({x}, {y})")

    @pyqtSlot(float)
    def reset_pose(self, duration_ms: float = 3000.0):
        """?? 强制回正头部和身体（用于TTS说话时）
        duration_ms: 回正保持时间（毫秒）
        """
        if self.live2d_view:
            logger.info(f"?? SpriteWindow: 强制回正姿势（{duration_ms}ms）")
            self.live2d_view.reset_pose(duration_ms)

    @pyqtSlot(int, int)
    def set_position(self, x: int, y: int):
        """设置窗口位置"""
        self.move(x, y)
        logger.info(f"?? Window moved to ({x}, {y})")

    @pyqtSlot(float)
    def set_opacity(self, opacity: float):
        """设置窗口透明度 (0.0 - 1.0)"""
        opacity = max(0.0, min(1.0, opacity))
        self.setWindowOpacity(opacity)
        logger.info(f"?? Window opacity set to {opacity}")

    @pyqtSlot(str, int)
    def trigger_motion(self, group: str, index: int = 0):
        """触发动作/动画"""
        if self.live2d_view:
            self.live2d_view.trigger_motion(group, index)
            logger.info(f"?? Motion triggered: {group}[{index}]")

    @pyqtSlot(str, int)
    def show_message(self, text: str, duration: int = 5000):
        if self.bubble_widget:
            self.bubble_widget.show_message(text, duration)

    def _switch_tts_provider(self, provider_name: str):
        """Switch TTS provider"""
        if self.tts_manager:
            success = self.tts_manager.set_provider(provider_name)
            if success:
                self.show_message(f"??? 已切换到: {provider_name.title()}")
            else:
                self.show_message(f"? 切换失败: {provider_name}")

    def _test_tts(self, text: str):
        """Test TTS with given text"""
        if not HAS_TTS or not self.tts_manager:
            self.show_message("? TTS 不可用")
            return

        # Show message
        self.show_message(f"??? {text}")

        # Run TTS in background thread to avoid blocking UI
        import threading
        def run_tts(tts_text):
            try:
                result = self.tts_manager.speak_sync(tts_text)
                if not result.success:
                    logger.error(f"TTS failed: {result.error}")
            except Exception as e:
                logger.error(f"TTS error: {e}")

        thread = threading.Thread(target=run_tts, args=(text,), daemon=True)
        thread.start()

    def _toggle_lip_sync(self):
        """Toggle lip sync"""
        if self.live2d_view and hasattr(self.live2d_view, 'set_lip_sync_enabled'):
            current = getattr(self.live2d_view, '_lip_sync_enabled', True)
            self.live2d_view.set_lip_sync_enabled(not current)
            new_state = not current
            self.show_message(f"?? 口型同步: {'开启' if new_state else '关闭'}")

    def _get_tts_state(self) -> bool:
        """Get current TTS state from backend"""
        try:
            import urllib.request
            import urllib.error
            import json
            
            data = json.dumps({"action": "status"}).encode('utf-8')
            
            req = urllib.request.Request(
                "http://127.0.0.1:8766/api/tts",
                data=data,
                headers={'Content-Type': 'application/json'},
                method='POST'
            )
            
            with urllib.request.urlopen(req, timeout=1) as response:
                if response.status == 200:
                    result = json.loads(response.read().decode('utf-8'))
                    return result.get('tts_enabled', True)
        except Exception as e:
            logger.debug(f"Failed to get TTS state: {e}")
        
        # Default to enabled if backend not available
        return True

    def _toggle_tts_master(self, checked: bool):
        """Toggle TTS master switch via HTTP API"""
        from PyQt6.QtCore import QTimer
        
        def send_tts_request():
            try:
                import urllib.request
                import urllib.error
                import json
                
                action = "on" if checked else "off"
                data = json.dumps({"action": action}).encode('utf-8')
                
                req = urllib.request.Request(
                    "http://127.0.0.1:8766/api/tts",
                    data=data,
                    headers={'Content-Type': 'application/json'},
                    method='POST'
                )
                
                with urllib.request.urlopen(req, timeout=2) as response:
                    if response.status == 200:
                        self.show_message(f"??? 语音 (TTS): {'开启' if checked else '关闭'}")
                    else:
                        self.show_message(f"?? TTS 状态已切换 (HTTP {response.status})")
                        
            except urllib.error.URLError as e:
                logger.error(f"TTS HTTP request failed: {e}")
                self.show_message(f"?? TTS 状态已切换 (后端未响应)")
            except Exception as e:
                logger.error(f"TTS toggle error: {e}")
                self.show_message(f"?? TTS 状态已切换")
        
        # Use QTimer to avoid blocking UI
        QTimer.singleShot(0, send_tts_request)

    def _toggle_eye_tracking(self):
        """Toggle eye tracking"""
        if self.live2d_view and hasattr(self.live2d_view, 'set_eye_tracking_enabled'):
            current = getattr(self.live2d_view, '_eye_tracking_enabled', True)
            self.live2d_view.set_eye_tracking_enabled(not current)
            new_state = not current
            self.show_message(f"??? 视线跟随: {'开启' if new_state else '关闭'}")

    def closeEvent(self, event):
        """窗口关闭事件 - 清理资源"""
        logger.info("?? 窗口关闭，清理资源...")
        
        # 清理 Live2D 视图
        if self.live2d_view:
            try:
                self.live2d_view.cleanup()
                logger.debug("? Live2D 视图已清理")
            except Exception as e:
                logger.warning(f"清理 Live2D 视图时出错: {e}")
        
        # 清理 TTS 管理器
        if self.tts_manager:
            try:
                self.tts_manager.cleanup()
                logger.debug("? TTS 管理器已清理")
            except Exception as e:
                logger.warning(f"清理 TTS 管理器时出错: {e}")
        
        # 接受关闭事件
        event.accept()
        logger.info("?? 窗口已关闭")

            
