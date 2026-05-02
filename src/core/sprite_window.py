#!/usr/bin/env python3
"""
Sherry Sprite Window - Transparent, Frameless, Always-on-Top
"""

import sys
import platform
from pathlib import Path

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QFrame, QVBoxLayout, QStackedLayout,
    QApplication, QSystemTrayIcon, QMenu
)
from PyQt6.QtCore import Qt, QPoint, QRectF, QTimer, QProcess, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QIcon, QAction, QFont, QPainter, QPainterPath, QLinearGradient, QColor, QPixmap
from loguru import logger

from src.ui.bubble_widget import BubbleWidget
try:
    from src.core.live2d_view import Live2DView, HAS_LIVE2D
except ImportError:
    HAS_LIVE2D = False

try:
    from src.core.vrm_view import VrmView, HAS_VRM_WEBENGINE
except ImportError:
    HAS_VRM_WEBENGINE = False

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


class BackgroundFrame(QFrame):
    """Custom-painted background frame to avoid QSS/GL composition issues."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._bg_type = "transparent"
        self._image_path = None
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAutoFillBackground(False)

    def set_background(self, bg_type: str):
        self._bg_type = bg_type
        self._image_path = None
        if bg_type.startswith("image:"):
            p = Path(bg_type[6:]).expanduser().resolve()
            if p.exists():
                self._image_path = str(p)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        rect = self.rect()
        if rect.width() <= 0 or rect.height() <= 0:
            return

        path = QPainterPath()
        path.addRoundedRect(QRectF(rect.adjusted(0, 0, -1, -1)), 20, 20)
        painter.setClipPath(path)

        if self._bg_type == "transparent":
            return

        if self._bg_type == "purple":
            grad = QLinearGradient(0, 0, rect.width(), rect.height())
            grad.setColorAt(0.0, QColor("#667eea"))
            grad.setColorAt(1.0, QColor("#764ba2"))
            painter.fillRect(rect, grad)
            return

        if self._image_path:
            pix = QPixmap(self._image_path)
            if not pix.isNull():
                scaled = pix.scaled(
                    rect.size(),
                    Qt.AspectRatioMode.IgnoreAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                painter.drawPixmap(rect.topLeft(), scaled)
                return

        color = QColor(self._bg_type)
        if color.isValid():
            painter.fillRect(rect, color)


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
        self.renderer_mode = self._load_renderer_mode()
        self.is_click_through = False
        self.is_big_head = False
        self._watermark_enabled = False
        self._current_background = "transparent"

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
            Qt.WindowType.WindowDoesNotAcceptFocus |
            Qt.WindowType.Tool
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
       
        # Keep top-level window undecorated/translucent; background is painted by central_widget.

    def _load_renderer_mode(self) -> str:
        """Read the preferred character renderer from config.yaml."""
        try:
            import yaml
            config_path = Path(get_resource_path("config.yaml"))
            if config_path.exists():
                with open(config_path, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f) or {}
                renderer = data.get("sprite", {}).get("renderer", "live2d")
                return str(renderer).strip().lower()
        except Exception as e:
            logger.warning(f"Failed to read renderer config, using Live2D: {e}")
        return "live2d"

    def _load_model_path_for_renderer(self) -> str:
        """Read the model path for the active renderer."""
        try:
            import yaml
            config_path = Path(get_resource_path("config.yaml"))
            if config_path.exists():
                with open(config_path, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f) or {}
                sprite = data.get("sprite", {})
                if self.renderer_mode == "vrm":
                    vrm_path = sprite.get("vrm", {}).get("path")
                    if vrm_path:
                        return get_resource_path(vrm_path)
                model_path = sprite.get("model", {}).get("path")
                if model_path:
                    return get_resource_path(model_path)
        except Exception as e:
            logger.warning(f"Failed to read model path config: {e}")

        if self.renderer_mode == "vrm":
            return get_resource_path("src/assets/models/vrm")
        return get_resource_path("src/assets/models/hanamaru")

    def _create_vrm_view(self):
        if not HAS_VRM_WEBENGINE:
            logger.error("VRM renderer requested but PyQt6-WebEngine is not installed")
            return None
        view = VrmView(self.central_widget)
        view.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        view.model_loaded.connect(self._auto_remove_watermark)
        view.touched.connect(self._on_touched)
        model_path = self._load_model_path_for_renderer()
        logger.info(f"Loading VRM model from: {model_path}")
        success = view.load_model(model_path)
        logger.info(f"VRM model load result: {success}")
        return view

    def _setup_ui(self):
        # 创建主容器
        self.central_widget = QFrame()
        self.central_widget.setFrameShape(QFrame.Shape.NoFrame)
        self.central_widget.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.central_widget.setObjectName("centralWidget")
        self.central_widget.setStyleSheet("background: transparent;")
        self.setCentralWidget(self.central_widget)
        
        layout = QStackedLayout(self.central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setStackingMode(QStackedLayout.StackingMode.StackAll)

        # 🚨 【关键】创建 Live2D 视图（必须在背景之前创建，以便背景可以设为它的 sibling）
        self.live2d_view = None
        logger.info(f"Character renderer mode: {self.renderer_mode}")
        if self.renderer_mode == "vrm":
            try:
                self.live2d_view = self._create_vrm_view()
                if self.live2d_view:
                    layout.addWidget(self.live2d_view)
                    logger.info("VRM view created and added to layout")
            except Exception as e:
                logger.error(f"Failed to initialize VRM renderer: {e}")
                import traceback
                logger.error(traceback.format_exc())
        elif HAS_LIVE2D:
            try:
                logger.info("🎨 Creating Live2DView...")
                self.live2d_view = Live2DView(self.central_widget)
                self.live2d_view.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
                layout.addWidget(self.live2d_view)
                logger.info("✅ Live2DView created and added to layout")
                
                # Connect model loaded signal for auto watermark removal
                self.live2d_view.model_loaded.connect(self._auto_remove_watermark)
                # 🚨 【触觉反馈】连接触摸信号到窗口级信号
                self.live2d_view.touched.connect(self._on_touched)
                
                # 加载模型 - 使用 get_resource_path 确保打包后路径正确
                model_path = self._load_model_path_for_renderer()
                logger.info(f"📂 Loading model from: {model_path}")
                
                # 检查路径是否存在
                import os
                if os.path.exists(model_path):
                    logger.info(f"✅ Model path exists: {model_path}")
                    # 列出目录内容
                    try:
                        files = os.listdir(model_path)
                        logger.info(f"📄 Files in model dir: {files}")
                    except Exception as e:
                        logger.warning(f"⚠️ Cannot list model dir: {e}")
                else:
                    logger.error(f"❌ Model path does NOT exist: {model_path}")
                
                success = self.live2d_view.load_model(model_path)
                logger.info(f"🎯 Model load result: {success}")
                
            except Exception as e:
                logger.error(f"❌ Failed to initialize Live2D: {e}")
                import traceback
                logger.error(traceback.format_exc())
        else:
            logger.error("❌ HAS_LIVE2D is False, skipping Live2D initialization")
        
        # 创建背景层 - 与 Live2DView 同级
        self.background_frame = BackgroundFrame(self.central_widget)
        self.background_frame.setGeometry(self.central_widget.rect())
        layout.addWidget(self.background_frame)
        
        # 🚨 【关键】如果有 Live2D，让背景位于 OpenGL 视图之下
        if self.live2d_view:
            self.background_frame.stackUnder(self.live2d_view)
            # 🚨 【关键】设置 OpenGL 视图始终在最上层绘制，但保持透明
            self.live2d_view.setAttribute(Qt.WidgetAttribute.WA_AlwaysStackOnTop, False)
            logger.info("✅ Background stacked under Live2DView")

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
            
        # 2. 🚨 窗口层级穿透：使用 Qt 原生系统标志，它会自动调用 macOS 底层的忽略鼠标 API
        self.setWindowFlag(Qt.WindowType.WindowTransparentForInput, enabled)
        
        # 3. 🚨 极其关键：在运行时修改 WindowFlag 会导致底层原生窗口被重置，必须调用 show() 将状态推送到系统！
        self.show()
        
        logger.info(f"🖱️ Click-through {'enabled' if enabled else 'disabled'}")
        
    @pyqtSlot(str)
    def set_background(self, bg_type: str):
        """设置窗口背景 - 支持纯色、渐变、透明和本地图片路径"""
        if not self.central_widget:
            logger.warning("set_background skipped: central_widget is not ready")
            return
        if bg_type.startswith("image:"):
            abs_path = Path(bg_type[6:]).expanduser().resolve()
            if not abs_path.exists():
                logger.error(f"Background image not found: {abs_path}")
                self.show_message(f"Image not found: {abs_path.name}")
                return

        if hasattr(self, "background_frame") and self.background_frame:
            self.background_frame.set_background(bg_type)
            self.background_frame.update()
            logger.info(f"Background frame active: size={self.background_frame.size()}")
        self._current_background = bg_type
        self.central_widget.update()
        logger.info(f"Background paint mode applied: {bg_type}")

        # 🚨 【关键】同时设置 Live2DView 的背景，因为 QOpenGLWidget 会覆盖 QWidget 的绘制
        if self.live2d_view:
            if bg_type == "transparent":
                self.live2d_view.set_background_color(None)
            elif bg_type == "purple":
                # 🎨 好看的紫色渐变: #667eea (102, 126, 234) -> #764ba2 (118, 75, 162)
                self.live2d_view.set_gradient_background((102, 126, 234), (118, 75, 162), "diagonal")
            elif bg_type.startswith("image:"):
                # 🎨 图片背景 - 直接在 Live2DView 中绘制
                image_path = bg_type[6:]
                self.live2d_view.set_background_image(image_path)
            else:
                # 纯色背景
                from PyQt6.QtGui import QColor
                color = QColor(bg_type)
                if color.isValid():
                    self.live2d_view.set_background_color((color.red(), color.green(), color.blue(), 255))
                else:
                    self.live2d_view.set_background_color(None)
            self.live2d_view.update()

        # 🚨 【关键修复】确保 Live2D 视图在最上层，防止背景覆盖模型
        if self.live2d_view:
            self.live2d_view.raise_()
            logger.debug("Live2D view raised to top")

        logger.info(f"Background updated: {self._current_background}")
            
    def toggle_big_head_mode(self, checked: bool = False):
        self.is_big_head = not self.is_big_head
        if self.is_big_head:
            self.setFixedSize(400, 400)
        else:
            self.setFixedSize(400, 600)
        self._position_bottom_right()
        if self.live2d_view:
            self.live2d_view.set_big_head_mode(self.is_big_head)

    def _renderer_supports(self, feature: str) -> bool:
        if not self.live2d_view:
            return False
        if hasattr(self.live2d_view, "supports_feature"):
            return bool(self.live2d_view.supports_feature(feature))
        return True

    def _get_config_path(self) -> Path:
        return Path(get_resource_path("config.yaml"))

    def _read_config_data(self) -> dict:
        try:
            import yaml
            config_path = self._get_config_path()
            if config_path.exists():
                with open(config_path, "r", encoding="utf-8") as f:
                    return yaml.safe_load(f) or {}
        except Exception as e:
            logger.error(f"Failed to read config: {e}")
        return {}

    def _write_config_data(self, data: dict) -> bool:
        try:
            import yaml
            config_path = self._get_config_path()
            with open(config_path, "w", encoding="utf-8") as f:
                yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False)
            return True
        except Exception as e:
            logger.error(f"Failed to write config: {e}")
            return False

    def _switch_renderer(self, renderer: str):
        renderer = str(renderer).strip().lower()
        if renderer == self.renderer_mode:
            self.show_message(f"Already using {renderer}")
            return

        if renderer == "vrm" and not HAS_VRM_WEBENGINE:
            self.show_message("VRM renderer is not available")
            return

        if renderer == "live2d" and not HAS_LIVE2D:
            self.show_message("Live2D renderer is not available")
            return

        data = self._read_config_data()
        sprite = data.setdefault("sprite", {})
        sprite["renderer"] = renderer

        if not self._write_config_data(data):
            self.show_message("Failed to save renderer selection")
            return

        self.show_message(f"Switching to {renderer} and restarting...")
        logger.info(f"Renderer changed to {renderer}, restarting application")
        QTimer.singleShot(200, self._restart_application)

    def _list_vrm_model_files(self) -> list[Path]:
        base_dir = Path(get_resource_path("src/assets/models/vrm"))
        if not base_dir.exists():
            return []

        candidates = []
        for pattern in ("*.vrm", "*.glb", "*.gltf"):
            candidates.extend(base_dir.rglob(pattern))
        return sorted([path for path in candidates if path.is_file()], key=lambda p: p.name.lower())

    def _get_current_vrm_path(self) -> str:
        data = self._read_config_data()
        sprite = data.get("sprite", {})
        vrm_path = sprite.get("vrm", {}).get("path")
        return str(vrm_path).replace("\\", "/") if vrm_path else ""

    def _switch_vrm_model(self, model_path: Path):
        try:
            rel_path = model_path.resolve().relative_to(Path(get_resource_path(".")).resolve())
        except Exception:
            rel_path = model_path

        rel_str = str(rel_path).replace("\\", "/")
        current = self._get_current_vrm_path()
        if current == rel_str:
            self.show_message(f"Already using {model_path.name}")
            return

        data = self._read_config_data()
        sprite = data.setdefault("sprite", {})
        vrm_cfg = sprite.setdefault("vrm", {})
        vrm_cfg["path"] = rel_str

        if not self._write_config_data(data):
            self.show_message("Failed to save Blender model selection")
            return

        self.show_message(f"Switching Blender model to {model_path.name}...")
        logger.info(f"VRM model changed to {rel_str}, restarting application")
        QTimer.singleShot(200, self._restart_application)

    def _restart_application(self):
        try:
            if getattr(sys, "frozen", False):
                program = sys.executable
                args = []
            else:
                program = sys.executable
                args = sys.argv

            workdir = str(Path(__file__).resolve().parents[2])
            started = QProcess.startDetached(program, args, workdir)
            if not started:
                self.show_message("Restart failed. Please relaunch manually.")
                logger.error("Failed to restart application")
                return

            QApplication.quit()
        except Exception as e:
            logger.error(f"Failed to restart application: {e}")
            self.show_message("Restart failed. Please relaunch manually.")

    def _position_bottom_right(self):
        screen = QApplication.primaryScreen().geometry()
        x = screen.width() - self.width() - 20
        y = screen.height() - self.height() - 50
        self.move(x, y)

    def _show_context_menu(self, pos):
        menu = QMenu(self)
        can_use_expressions = self._renderer_supports("expression")
        can_use_watermark = self._renderer_supports("watermark")
        can_use_eye_tracking = self._renderer_supports("eye_tracking")
        can_use_lip_sync = self._renderer_supports("lip_sync")

        # Expression menu (Param-based)
        expr_menu = menu.addMenu("Expression")
        expr_menu.setEnabled(can_use_expressions)
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
        watermark_action.setEnabled(can_use_watermark)
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
        
        # Eye tracking toggle
        eye_action = QAction("👁️ 视线跟随 (Eye Tracking)", self)
        eye_action.setCheckable(True)
        eye_tracking_enabled = self.live2d_view and getattr(self.live2d_view, '_eye_tracking_enabled', True)
        eye_action.setChecked(eye_tracking_enabled)
        eye_action.triggered.connect(self._toggle_eye_tracking)
        eye_action.setEnabled(can_use_eye_tracking)
        menu.addAction(eye_action)

        renderer_menu = menu.addMenu("Renderer")

        blender_action = QAction("Blender / 3D Model", self)
        blender_action.setCheckable(True)
        blender_action.setChecked(self.renderer_mode == "vrm")
        blender_action.setEnabled(HAS_VRM_WEBENGINE)
        blender_action.triggered.connect(lambda checked=False: self._switch_renderer("vrm"))
        renderer_menu.addAction(blender_action)

        live2d_action = QAction("Live2D / 2D Model", self)
        live2d_action.setCheckable(True)
        live2d_action.setChecked(self.renderer_mode == "live2d")
        live2d_action.setEnabled(HAS_LIVE2D)
        live2d_action.triggered.connect(lambda checked=False: self._switch_renderer("live2d"))
        renderer_menu.addAction(live2d_action)

        blender_model_menu = renderer_menu.addMenu("Blender Model")
        blender_model_menu.setEnabled(self.renderer_mode == "vrm")
        current_vrm_path = self._get_current_vrm_path()
        vrm_models = self._list_vrm_model_files()
        if vrm_models:
            for model_path in vrm_models:
                try:
                    rel_path = model_path.resolve().relative_to(Path(get_resource_path(".")).resolve())
                    rel_str = str(rel_path).replace("\\", "/")
                except Exception:
                    rel_str = str(model_path).replace("\\", "/")

                action = QAction(model_path.name, self)
                action.setCheckable(True)
                action.setChecked(current_vrm_path == rel_str)
                action.triggered.connect(lambda checked=False, p=model_path: self._switch_vrm_model(p))
                blender_model_menu.addAction(action)
        else:
            no_model_action = QAction("No VRM/GLB models found", self)
            no_model_action.setEnabled(False)
            blender_model_menu.addAction(no_model_action)

        bg_menu = menu.addMenu("Background")
        bg_transparent_action = QAction("Transparent", self)
        bg_transparent_action.setCheckable(True)
        bg_transparent_action.setChecked(self._current_background == "transparent")
        bg_transparent_action.triggered.connect(lambda checked=False: self.set_background("transparent"))
        bg_menu.addAction(bg_transparent_action)

        bg_purple_action = QAction("Purple Gradient", self)
        bg_purple_action.setCheckable(True)
        bg_purple_action.setChecked(self._current_background == "purple")
        bg_purple_action.triggered.connect(lambda checked=False: self.set_background("purple"))
        bg_menu.addAction(bg_purple_action)

        bg_menu.addSeparator()
        for label, color in [
            ("White", "white"),
            ("Black", "black"),
            ("Light Gray", "#f5f5f5"),
            ("Light Blue", "#e3f2fd"),
            ("Light Pink", "#fce4ec"),
        ]:
            action = QAction(label, self)
            action.setCheckable(True)
            action.setChecked(self._current_background == color)
            action.triggered.connect(lambda checked=False, c=color: self.set_background(c))
            bg_menu.addAction(action)

        bg_menu.addSeparator()
        bg_image_action = QAction("Choose Image...", self)
        bg_image_action.triggered.connect(self._select_background_image)
        bg_menu.addAction(bg_image_action)

        menu.addSeparator()

        # 🎙️ TTS Test Menu
        tts_menu = menu.addMenu("🎙️ TTS 设置")

        # 🚨 TTS Master Switch
        tts_master_action = QAction("🗣️ 启用语音 (TTS)", self)
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

        # Language selection submenu
        lang_menu = tts_menu.addMenu("🌐 语言")
        languages = [
            ("🇨🇳 中文", "zh"),
            ("🇺🇸 English", "en"),
            ("🇯🇵 日本語", "ja"),
        ]
        if HAS_TTS and self.tts_manager:
            current_lang = getattr(self.tts_manager, '_current_language', 'zh')
            for label, lang_code in languages:
                action = QAction(label, self)
                action.setCheckable(True)
                action.setChecked(current_lang == lang_code)
                action.triggered.connect(lambda checked, l=lang_code: self._switch_language(l))
                lang_menu.addAction(action)
        else:
            no_lang_action = QAction("TTS 不可用", self)
            no_lang_action.setEnabled(False)
            lang_menu.addAction(no_lang_action)

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
            lip_sync_action = QAction("👄 口型同步", self)
            lip_sync_action.setCheckable(True)
            # Check if live2d_view has lip sync enabled
            lip_sync_enabled = True
            if self.live2d_view and hasattr(self.live2d_view, '_lip_sync_enabled'):
                lip_sync_enabled = self.live2d_view._lip_sync_enabled
            lip_sync_action.setChecked(lip_sync_enabled)
            lip_sync_action.triggered.connect(self._toggle_lip_sync)
            lip_sync_action.setEnabled(can_use_lip_sync)
            tts_menu.addAction(lip_sync_action)

        menu.addSeparator()
        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(QApplication.quit)
        menu.addAction(quit_action)

        menu.exec(pos)

    def _toggle_watermark(self):
        if not self._renderer_supports("watermark"):
            self.show_message("Current renderer does not need the watermark toggle")
            return
        self._watermark_enabled = not self._watermark_enabled
        val = -1.0 if self._watermark_enabled else 0.0
        self.set_parameter("Open_EyeMask4", val)
    
    def _auto_remove_watermark(self):
        """启动时自动去水印"""
        if not self._renderer_supports("watermark"):
            return
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
            if hasattr(self.live2d_view, "look_at"):
                self.live2d_view.look_at(x, y)
            else:
                self.live2d_view.mouse_x = x
                self.live2d_view.mouse_y = y
                self.live2d_view.update()
            logger.info(f"👀 Look at: ({x}, {y})")

    @pyqtSlot(float)
    def reset_pose(self, duration_ms: float = 3000.0):
        """🚨 强制回正头部和身体（用于TTS说话时）
        duration_ms: 回正保持时间（毫秒）
        """
        if self.live2d_view:
            logger.info(f"🎯 SpriteWindow: 强制回正姿势（{duration_ms}ms）")
            self.live2d_view.reset_pose(duration_ms)

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

    def _switch_language(self, lang_code: str):
        """Switch TTS language"""
        if self.tts_manager and hasattr(self.tts_manager, 'set_language'):
            success = self.tts_manager.set_language(lang_code)
            lang_names = {"zh": "中文", "en": "English", "ja": "日本語"}
            lang_name = lang_names.get(lang_code, lang_code)
            if success:
                self.show_message(f"🌐 语言已切换: {lang_name}")
            else:
                self.show_message(f"❌ 语言切换失败: {lang_name}")

    def _test_tts(self, text: str):
        """Test TTS with given text"""
        if not HAS_TTS or not self.tts_manager:
            self.show_message("❌ TTS 不可用")
            return

        # Show message
        self.show_message(f"🗣️ {text}")

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
            self.show_message(f"👄 口型同步: {'开启' if new_state else '关闭'}")

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
                        self.show_message(f"🗣️ 语音 (TTS): {'开启' if checked else '关闭'}")
                    else:
                        self.show_message(f"⚠️ TTS 状态已切换 (HTTP {response.status})")
                        
            except urllib.error.URLError as e:
                logger.error(f"TTS HTTP request failed: {e}")
                self.show_message(f"⚠️ TTS 状态已切换 (后端未响应)")
            except Exception as e:
                logger.error(f"TTS toggle error: {e}")
                self.show_message(f"⚠️ TTS 状态已切换")
        
        # Use QTimer to avoid blocking UI
        QTimer.singleShot(0, send_tts_request)

    def _toggle_eye_tracking(self):
        """Toggle eye tracking"""
        if self.live2d_view and hasattr(self.live2d_view, 'set_eye_tracking_enabled'):
            current = getattr(self.live2d_view, '_eye_tracking_enabled', True)
            self.live2d_view.set_eye_tracking_enabled(not current)
            new_state = not current
            self.show_message(f"👁️ 视线跟随: {'开启' if new_state else '关闭'}")

    def _select_background_image(self):
        """Open dialog to select a background image."""
        from PyQt6.QtWidgets import QFileDialog

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Background Image",
            str(Path.home()),
            "Image Files (*.png *.jpg *.jpeg *.bmp *.gif)"
        )

        if file_path:
            self.set_background(f"image:{file_path}")
            self.show_message("Background image updated")

    def closeEvent(self, event):
        """窗口关闭事件 - 清理资源"""
        logger.info("👋 窗口关闭，清理资源...")
        
        # 清理 Live2D 视图
        if self.live2d_view:
            try:
                self.live2d_view.cleanup()
                logger.debug("✅ Live2D 视图已清理")
            except Exception as e:
                logger.warning(f"清理 Live2D 视图时出错: {e}")
        
        # 清理 TTS 管理器
        if self.tts_manager:
            try:
                self.tts_manager.cleanup()
                logger.debug("✅ TTS 管理器已清理")
            except Exception as e:
                logger.warning(f"清理 TTS 管理器时出错: {e}")
        
        # 接受关闭事件
        event.accept()
        logger.info("👋 窗口已关闭")

            
