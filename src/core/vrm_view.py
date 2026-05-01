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

from PyQt6.QtCore import QObject, Qt, QUrl, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QWidget, QVBoxLayout
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

        self.web = QWebEngineView(self)
        self.page = LoggingWebPage(self.web)
        self.web.setPage(self.page)
        self.web.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
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

    def find_expression(self, name: str):
        if not name:
            return None
        key = name.lower()
        return name if key in self._expression_mapping else None

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
        self._run_js(
            "window.SherryVrm && window.SherryVrm.triggerMotion("
            f"{json.dumps(group)}, {json.dumps(index)});"
        )

    def reset_pose(self, duration_ms: float = 3000.0):
        self._run_js(f"window.SherryVrm && window.SherryVrm.resetPose({json.dumps(duration_ms)});")

    def set_big_head_mode(self, enabled: bool):
        self._run_js(f"window.SherryVrm && window.SherryVrm.setBigHeadMode({json.dumps(bool(enabled))});")

    def set_lip_sync_enabled(self, enabled: bool):
        self._lip_sync_enabled = bool(enabled)

    def set_eye_tracking_enabled(self, enabled: bool):
        self._eye_tracking_enabled = bool(enabled)
        self._run_js(f"window.SherryVrm && window.SherryVrm.setEyeTracking({json.dumps(bool(enabled))});")

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
        self._run_js("window.SherryVrm && window.SherryVrm.dispose();")

    def _on_viewer_ready(self):
        if self.model_path:
            self.load_model(self.model_path)
        else:
            self._run_js("window.SherryVrm && window.SherryVrm.loadFallback();")
        self.model_loaded.emit()

    def _run_js(self, script: str):
        if self.web:
            self.web.page().runJavaScript(script)
