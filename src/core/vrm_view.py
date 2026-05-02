#!/usr/bin/env python3
"""
VRM/Three.js character view hosted in QWebEngine.

Blender stays in the asset pipeline: export a VRM, GLB, or GLTF file and this
widget renders it through Three.js. The public methods mirror Live2DView closely
enough for SpriteWindow/WebSocketServer to keep using the same command surface.
"""

import json
from pathlib import Path
from typing import Dict, Optional

from PyQt6.QtCore import QObject, QPoint, Qt, QTimer, QUrl, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QColor, QCursor, QMouseEvent
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout
from loguru import logger

try:
    from PyQt6.QtWebEngineWidgets import QWebEngineView
    from PyQt6.QtWebEngineCore import QWebEnginePage, QWebEngineSettings
    from PyQt6.QtWebChannel import QWebChannel
    HAS_VRM_WEBENGINE = True
except ImportError as e:
    QWebEngineView = None
    QWebChannel = None
    HAS_VRM_WEBENGINE = False
    logger.warning(f"PyQt6-WebEngine is not available: {e}")

try:
    from src.utils import get_resource_path
except ImportError:
    def get_resource_path(relative_path: str) -> str:
        return str(Path(__file__).resolve().parents[2] / relative_path)

try:
    from src.core.tts_manager import get_tts_manager
    HAS_TTS = True
except ImportError:
    HAS_TTS = False


class VrmBridge(QObject):
    touched = pyqtSignal(str, str)
    ready = pyqtSignal()

    @pyqtSlot(str, str)
    def emitTouched(self, action: str, part: str):
        self.touched.emit(action, part)

    @pyqtSlot()
    def emitReady(self):
        self.ready.emit()


class LoggingWebPage(QWebEnginePage):
    def javaScriptConsoleMessage(self, level, message, line_number, source_id):
        logger.info(f"VRM console[{level.name}] {source_id}:{line_number} {message}")


class InteractiveWebView(QWebEngineView):
    context_menu_requested = pyqtSignal(QPoint)
    tapped = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._drag_origin: Optional[QPoint] = None
        self._window_origin: Optional[QPoint] = None
        self._dragging = False

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            top_level = self.window()
            self._drag_origin = event.globalPosition().toPoint()
            self._window_origin = top_level.frameGeometry().topLeft() if top_level else None
            self._dragging = False
            event.accept()
            return

        if event.button() == Qt.MouseButton.RightButton:
            self.context_menu_requested.emit(event.globalPosition().toPoint())
            event.accept()
            return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        if self._drag_origin is not None and event.buttons() & Qt.MouseButton.LeftButton:
            top_level = self.window()
            if top_level and self._window_origin is not None:
                delta = event.globalPosition().toPoint() - self._drag_origin
                if delta.manhattanLength() >= QApplication.startDragDistance():
                    self._dragging = True
                top_level.move(self._window_origin + delta)
            event.accept()
            return

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton and self._drag_origin is not None:
            if not self._dragging:
                self.tapped.emit()
            self._drag_origin = None
            self._window_origin = None
            self._dragging = False
            event.accept()
            return

        super().mouseReleaseEvent(event)


class VrmView(QWidget):
    """QWebEngine wrapper that exposes a Live2D-like control API."""

    touched = pyqtSignal(str, str)
    model_loaded = pyqtSignal()

    _expression_mapping = {
        "normal": "neutral",
        "happy": "happy",
        "sad": "sad",
        "angry": "angry",
        "love": "relaxed",
        "blush": "happy",
        "daze": "surprised",
        "surprised": "surprised",
        "sleepy": "sleepy",
    }

    def __init__(self, parent=None, model_path: Optional[str] = None):
        super().__init__(parent)
        if not HAS_VRM_WEBENGINE:
            raise RuntimeError("PyQt6-WebEngine is required for the VRM renderer")

        self.model_path = model_path
        self.current_expression = "normal"
        self._params: Dict[str, float] = {}
        self._lip_sync_enabled = True
        self._eye_tracking_enabled = True
        self._pending_model_url: Optional[str] = None
        self._drag_origin: Optional[QPoint] = None
        self._window_origin: Optional[QPoint] = None
        self._dragging = False
        self._look_x = 0.0
        self._look_y = 0.0
        self._current_mouth_open = 0.0
        self._mouth_smooth_value = 0.0
        self._last_mouth_frame_ms = 0

        self.web = InteractiveWebView(self)
        self.page = LoggingWebPage(self.web)
        self.web.setPage(self.page)
        self.web.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.web.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.web.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
        self.web.page().setBackgroundColor(QColor(0, 0, 0, 0))
        self.web.settings().setAttribute(
            QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls,
            True,
        )
        self.web.settings().setAttribute(
            QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls,
            True,
        )

        self.bridge = VrmBridge()
        self.bridge.touched.connect(self.touched)
        self.bridge.ready.connect(self._on_viewer_ready)
        self.channel = QWebChannel(self.web.page())
        self.channel.registerObject("vrmBridge", self.bridge)
        self.web.page().setWebChannel(self.channel)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.web)

        self._eye_tracking_timer = QTimer(self)
        self._eye_tracking_timer.setInterval(33)
        self._eye_tracking_timer.timeout.connect(self._update_eye_tracking)
        self._eye_tracking_timer.start()

        self._lip_sync_timer = QTimer(self)
        self._lip_sync_timer.setInterval(16)
        self._lip_sync_timer.timeout.connect(self._update_lip_sync)
        self._lip_sync_timer.start()

        self._connect_tts_manager()

        viewer_path = Path(get_resource_path("src/assets/vrm_viewer/index.html"))
        self.web.setUrl(QUrl.fromLocalFile(str(viewer_path)))

    def load_model(self, model_path: str) -> bool:
        path = Path(model_path).expanduser()
        if path.is_dir():
            candidates = (
                list(path.glob("*.vrm"))
                + list(path.glob("*.glb"))
                + list(path.glob("*.gltf"))
            )
            path = candidates[0] if candidates else path / "sherry.vrm"

        if not path.exists():
            logger.warning(f"VRM model not found, using fallback scene: {path}")
            self._pending_model_url = None
            self._run_js("window.SherryVrm && window.SherryVrm.loadFallback();")
            return False

        self.model_path = str(path)
        self._pending_model_url = QUrl.fromLocalFile(str(path.resolve())).toString()
        self._run_js(f"window.SherryVrm && window.SherryVrm.loadModel({json.dumps(self._pending_model_url)});")
        logger.info(f"VRM model queued: {path}")
        return True

    def get_available_expressions(self):
        return list(self._expression_mapping.keys())

    def supports_feature(self, feature: str) -> bool:
        supported = {
            "expression": True,
            "parameter": True,
            "look_at": True,
            "motion": False,
            "reset_pose": False,
            "background": True,
            "big_head": True,
            "eye_tracking": True,
            "lip_sync": True,
            "watermark": False,
        }
        return supported.get(str(feature).strip().lower(), False)

    def find_expression(self, name: str):
        if not name:
            return None
        key = name.lower()
        if key in self._expression_mapping:
            return name
        if key in self._expression_mapping.values():
            return name
        return None

    def set_expression(self, name: str) -> bool:
        actual = self._expression_mapping.get(name.lower(), name)
        self.current_expression = name
        self._run_js(f"window.SherryVrm && window.SherryVrm.setExpression({json.dumps(actual)});")
        return True

    def set_parameter(self, param_id: str, value: float) -> bool:
        value = float(value)
        self._params[param_id] = value
        self._run_js(
            "window.SherryVrm && window.SherryVrm.setParameter("
            f"{json.dumps(param_id)}, {json.dumps(value)});"
        )
        return True

    def get_parameter(self, param_id: str) -> float:
        return self._params.get(param_id, 0.0)

    def trigger_motion(self, group: str, index: int = 0):
        logger.debug(f"VRM motion '{group}[{index}]' ignored: no Blender/3D animation mapping yet")

    def reset_pose(self, duration_ms: float = 3000.0):
        logger.debug(f"VRM reset_pose ignored ({duration_ms}ms): pose reset is not used in Blender/3D mode")

    def set_big_head_mode(self, enabled: bool):
        self._run_js(f"window.SherryVrm && window.SherryVrm.setBigHeadMode({json.dumps(bool(enabled))});")

    def set_lip_sync_enabled(self, enabled: bool):
        self._lip_sync_enabled = bool(enabled)
        if not self._lip_sync_enabled:
            self._current_mouth_open = 0.0
            self._mouth_smooth_value = 0.0
            self.set_parameter("ParamMouthOpenY", 0.0)
        self._run_js(f"window.SherryVrm && window.SherryVrm.setLipSync({json.dumps(bool(enabled))});")

    def set_eye_tracking_enabled(self, enabled: bool):
        self._eye_tracking_enabled = bool(enabled)
        self._run_js(f"window.SherryVrm && window.SherryVrm.setEyeTracking({json.dumps(bool(enabled))});")

    def look_at(self, x: float, y: float):
        self._look_x = float(x)
        self._look_y = float(y)
        self._run_js(
            "window.SherryVrm && window.SherryVrm.lookAt("
            f"{json.dumps(float(x))}, {json.dumps(float(y))});"
        )

    def set_background_color(self, color):
        self._run_js(f"window.SherryVrm && window.SherryVrm.setBackground({json.dumps(color)});")

    def set_gradient_background(self, color1, color2, direction="diagonal"):
        self._run_js(
            "window.SherryVrm && window.SherryVrm.setGradientBackground("
            f"{json.dumps(color1)}, {json.dumps(color2)}, {json.dumps(direction)});"
        )

    def set_background_image(self, image_path: str):
        url = QUrl.fromLocalFile(str(Path(image_path).expanduser().resolve())).toString()
        self._run_js(f"window.SherryVrm && window.SherryVrm.setBackgroundImage({json.dumps(url)});")

    def cleanup(self):
        self._eye_tracking_timer.stop()
        self._lip_sync_timer.stop()
        self._run_js("window.SherryVrm && window.SherryVrm.dispose();")

    def _connect_tts_manager(self):
        if HAS_TTS:
            try:
                tts = get_tts_manager()
                tts.lip_sync_frame.connect(self._on_lip_sync_frame)
                logger.info("Lip sync connected to TTS manager for VRM view")
            except Exception as e:
                logger.warning(f"Failed to connect VRM lip sync to TTS manager: {e}")

    def _on_viewer_ready(self):
        if self.model_path:
            self.load_model(self.model_path)
        else:
            self._run_js("window.SherryVrm && window.SherryVrm.loadFallback();")
        self.model_loaded.emit()

    @pyqtSlot(float)
    def _on_lip_sync_frame(self, mouth_open: float):
        if self._lip_sync_enabled:
            scaled = float(mouth_open) * 0.68
            self._current_mouth_open = max(0.0, min(0.72, scaled))
            self._last_mouth_frame_ms = 0

    def _run_js(self, script: str):
        if self.web:
            self.web.page().runJavaScript(script)

    def _update_lip_sync(self):
        if not self._lip_sync_enabled:
            return

        self._last_mouth_frame_ms += self._lip_sync_timer.interval()
        if self._last_mouth_frame_ms > 120:
            self._current_mouth_open = 0.0

        smoothing_factor = 0.35
        self._mouth_smooth_value += (self._current_mouth_open - self._mouth_smooth_value) * smoothing_factor

        previous = self._params.get("ParamMouthOpenY", 0.0)
        if abs(previous - self._mouth_smooth_value) >= 0.01:
            self.set_parameter("ParamMouthOpenY", self._mouth_smooth_value)

    def _update_eye_tracking(self):
        if not self._eye_tracking_enabled or not self.isVisible():
            return

        try:
            window_pos = self.mapToGlobal(QPoint(0, 0))
            win_x = window_pos.x()
            win_y = window_pos.y()
            win_w = max(1, self.width())
            win_h = max(1, self.height())

            center_x = win_x + win_w / 2
            center_y = win_y + win_h / 2

            mouse_pos = QCursor.pos()
            sensitivity = 1.35
            offset_x = ((mouse_pos.x() - center_x) / (win_w / 2)) * sensitivity
            offset_y = -((mouse_pos.y() - center_y) / (win_h / 2)) * sensitivity

            offset_x = max(-1.0, min(1.0, offset_x))
            offset_y = max(-1.0, min(1.0, offset_y))

            dead_zone = 0.06
            if abs(offset_x) < dead_zone:
                offset_x = 0.0
            if abs(offset_y) < dead_zone:
                offset_y = 0.0

            smoothed_x = self._look_x * 0.7 + offset_x * 0.3
            smoothed_y = self._look_y * 0.7 + offset_y * 0.3
            self.look_at(smoothed_x, smoothed_y)
        except Exception as e:
            logger.debug(f"VRM eye tracking update failed: {e}")

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            top_level = self.window()
            self._drag_origin = event.globalPosition().toPoint()
            self._window_origin = top_level.frameGeometry().topLeft() if top_level else None
            self._dragging = False
            event.accept()
            return

        if event.button() == Qt.MouseButton.RightButton:
            top_level = self.window()
            if top_level and hasattr(top_level, "_show_context_menu"):
                top_level._show_context_menu(event.globalPosition().toPoint())
            event.accept()
            return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        if self._drag_origin is not None and event.buttons() & Qt.MouseButton.LeftButton:
            top_level = self.window()
            if top_level and self._window_origin is not None:
                delta = event.globalPosition().toPoint() - self._drag_origin
                if delta.manhattanLength() >= QApplication.startDragDistance():
                    self._dragging = True
                top_level.move(self._window_origin + delta)
            event.accept()
            return

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton and self._drag_origin is not None:
            if not self._dragging:
                self.touched.emit("tap", "body")
            self._drag_origin = None
            self._window_origin = None
            self._dragging = False
            event.accept()
            return

        super().mouseReleaseEvent(event)
