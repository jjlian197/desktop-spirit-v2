#!/usr/bin/env python3
"""
Sherry Sprite Window - Transparent, Frameless, Always-on-Top
"""

import sys
import os
import platform
from pathlib import Path

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout,
    QApplication, QSystemTrayIcon, QMenu
)
from PyQt6.QtCore import Qt, QPoint, QTimer, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QIcon, QAction, QFont, QPalette, QColor, QGradient, QLinearGradient ,QSurfaceFormat
from loguru import logger

from src.ui.bubble_widget import BubbleWidget
try:
    from src.core.live2d_view import Live2DView, HAS_LIVE2D
except ImportError:
    HAS_LIVE2D = False

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
    
    # 🚨 【触觉反馈】触摸事件信号 - 当用户触摸雪莉时发射
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
                logger.info("✅ SpriteWindow: TTS manager initialized")
            except Exception as e:
                logger.error(f"Failed to initialize TTS manager: {e}")

        # Setup window properties
        self._setup_window()
        self._setup_ui()
        self._setup_tray()
        self._position_bottom_right()

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
       
        self.setStyleSheet("SherrySpriteWindow { background: transparent; }")
        
    def _setup_ui(self):
        self.central_widget = QWidget()
        self.central_widget.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.central_widget.setObjectName("centralWidget")
        self.central_widget.setStyleSheet("#centralWidget { background: transparent; }")
        self.setCentralWidget(self.central_widget)

        layout = QVBoxLayout(self.central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.live2d_view = None
        if HAS_LIVE2D:
            try:
                self.live2d_view = Live2DView(self.central_widget)
                # 确保 OpenGL 部件本身不遮挡背景
                self.live2d_view.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
                self.live2d_view.setAttribute(Qt.WidgetAttribute.WA_AlwaysStackOnTop)
                layout.addWidget(self.live2d_view)
                # Connect model loaded signal for auto watermark removal
                self.live2d_view.model_loaded.connect(self._auto_remove_watermark)
                # 🚨 【触觉反馈】连接触摸信号到窗口级信号
                self.live2d_view.touched.connect(self._on_touched)
                # Use built-in model from project assets
                model_path = os.path.join(os.path.dirname(__file__), "../assets/models/hanamaru")
                self.live2d_view.load_model(model_path)
            except Exception as e:
                logger.error(f"Failed to initialize Live2D: {e}")

        self.bubble_widget = BubbleWidget(self)
        self.bubble_widget.hide()
        self.message_received.connect(self.show_message)

    def _setup_tray(self):
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return
        self.tray_icon = QSystemTrayIcon(self)
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
            
        # 2. 🚨 窗口层级穿透：使用 Qt 原生系统标志，它会自动调用 macOS 底层的忽略鼠标 API
        self.setWindowFlag(Qt.WindowType.WindowTransparentForInput, enabled)
        
        # 3. 🚨 极其关键：在运行时修改 WindowFlag 会导致底层原生窗口被重置，必须调用 show() 将状态推送到系统！
        self.show()
        
        logger.info(f"🖱️ Click-through {'enabled' if enabled else 'disabled'}")
        
    @pyqtSlot(str)
    def set_background(self, bg_type: str):
        """设置窗口背景 - 支持纯色、渐变、透明和本地图片路径"""
        if bg_type == "purple":
            # 渐变紫色 - 使用样式表
            self.central_widget.setStyleSheet("""
                #centralWidget {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #667eea, stop:1 #764ba2);
                    border-radius: 20px;
                }
            """)
            logger.info("🎨 Background set to Purple Gradient")
            
        elif bg_type == "transparent":
            # 透明背景
            self.central_widget.setStyleSheet("#centralWidget { background: transparent; }")
            logger.info("🎨 Background set to Transparent")
            
        elif bg_type.startswith("image:"):
            # 图片背景
            image_path = bg_type[6:]
            from pathlib import Path
            abs_path = Path(image_path).expanduser().resolve()
            
            if not abs_path.exists():
                logger.error(f"❌ 背景图片不存在: {abs_path}")
                return
                
            safe_path = str(abs_path).replace('\\', '/')
            style = f"""
                #centralWidget {{
                    border-image: url("{safe_path}") 0 0 0 0 stretch stretch;
                    border-radius: 20px;
                }}
            """
            self.central_widget.setStyleSheet(style)
            logger.info(f"🎨 Background set to image: {safe_path}")
            
        else:
            # 纯色背景
            self.central_widget.setStyleSheet(f"#centralWidget {{ background: {bg_type}; border-radius: 20px; }}")
            logger.info(f"🎨 Background set to custom: {bg_type}")
            
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
        ct_action = QAction("🖱️ 鼠标穿透 (Click Through)", self)
        ct_action.setCheckable(True)
        ct_action.setChecked(self.is_click_through)
        ct_action.triggered.connect(self.set_click_through)
        menu.addAction(ct_action)

        # Big head mode toggle
        bh_action = QAction("👤 大头模式 (Big Head Mode)", self)
        bh_action.setCheckable(True)
        bh_action.setChecked(self.is_big_head)
        bh_action.triggered.connect(self.toggle_big_head_mode)
        menu.addAction(bh_action)

        menu.addSeparator()

        # 🎙️ TTS Test Menu
        tts_menu = menu.addMenu("🎙️ TTS 测试")

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

        for label, text in test_phrases:
            action = QAction(label, self)
            action.triggered.connect(lambda checked, t=text: self._test_tts(t))
            tts_menu.addAction(action)

        # Lip sync toggle
        if HAS_TTS and self.tts_manager:
            tts_menu.addSeparator()
            lip_sync_action = QAction("👄 口型同步", self)
            lip_sync_action.setCheckable(True)
            # Check if live2d_view has lip sync enabled
            lip_sync_enabled = True
            if self.live2d_view and hasattr(self.live2d_view, '_lip_sync_enabled'):
                lip_sync_enabled = self.live2d_view._lip_sync_enabled
            lip_sync_action.setChecked(lip_sync_enabled)
            lip_sync_action.triggered.connect(self._toggle_lip_sync)
            tts_menu.addAction(lip_sync_action)

        menu.addSeparator()

        # 背景菜单
        bg_menu = menu.addMenu("🎨 背景 (Background)")
        trans_bg = QAction("透明 (Transparent)", self)
        trans_bg.triggered.connect(lambda: self.set_background("transparent"))
        bg_menu.addAction(trans_bg)
        
        purple_bg = QAction("渐变紫 (Purple Gradient)", self)
        purple_bg.triggered.connect(lambda: self.set_background("purple"))
        bg_menu.addAction(purple_bg)

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
        logger.info("🎭 已自动启用去水印")
    
    def _on_touched(self, action: str, part: str):
        """🚨 【触觉反馈】处理触摸事件，转发到大脑"""
        logger.info(f"💖 雪莉感受到了主人的{action}，部位: {part}")
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
        
        # 眼神跟随：即使没有点击，只要鼠标在窗口内移动，就通知 Live2DView
        if self.live2d_view:
            # 将事件传递给子控件
            self.live2d_view.mouseMoveEvent(event)

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
            logger.info(f"👀 Look at: ({x}, {y})")

    @pyqtSlot(int, int)
    def set_position(self, x: int, y: int):
        """设置窗口位置"""
        self.move(x, y)
        logger.info(f"📍 Window moved to ({x}, {y})")

    @pyqtSlot(float)
    def set_opacity(self, opacity: float):
        """设置窗口透明度 (0.0 - 1.0)"""
        opacity = max(0.0, min(1.0, opacity))
        self.setWindowOpacity(opacity)
        logger.info(f"👻 Window opacity set to {opacity}")

    @pyqtSlot(str, int)
    def trigger_motion(self, group: str, index: int = 0):
        """触发动作/动画"""
        if self.live2d_view:
            self.live2d_view.trigger_motion(group, index)
            logger.info(f"🎬 Motion triggered: {group}[{index}]")

    @pyqtSlot(str, int)
    def show_message(self, text: str, duration: int = 5000):
        if self.bubble_widget:
            self.bubble_widget.show_message(text, duration)

    def _switch_tts_provider(self, provider_name: str):
        """Switch TTS provider"""
        if self.tts_manager:
            success = self.tts_manager.set_provider(provider_name)
            if success:
                self.show_message(f"🎙️ 已切换到: {provider_name.title()}")
            else:
                self.show_message(f"❌ 切换失败: {provider_name}")

    def _test_tts(self, text: str):
        """Test TTS with given text"""
        if not HAS_TTS or not self.tts_manager:
            self.show_message("❌ TTS 不可用")
            return

        # Show message
        self.show_message(f"🗣️ {text}")

        # Run TTS in background thread to avoid blocking UI
        import threading
        def run_tts():
            try:
                result = self.tts_manager.speak_sync(text)
                if not result.success:
                    logger.error(f"TTS failed: {result.error}")
            except Exception as e:
                logger.error(f"TTS error: {e}")

        thread = threading.Thread(target=run_tts, daemon=True)
        thread.start()

    def _toggle_lip_sync(self):
        """Toggle lip sync"""
        if self.live2d_view and hasattr(self.live2d_view, 'set_lip_sync_enabled'):
            current = getattr(self.live2d_view, '_lip_sync_enabled', True)
            self.live2d_view.set_lip_sync_enabled(not current)
            new_state = not current
            self.show_message(f"👄 口型同步: {'开启' if new_state else '关闭'}")

            
