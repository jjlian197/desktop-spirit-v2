#!/usr/bin/env python3
"""
Live2D View - OpenGL-based Live2D model rendering
Uses live2d-py for Python bindings to Live2D Cubism SDK

⚠️  APPLE SILICON (M1/M2/M3/M4) FIXES:
- MUST call live2d.glInit() BEFORE live2d.init() inside initializeGL()
- OpenGL context must be current before any Live2D operations
- Model loading must happen after glInit() and init()
"""

import os
import platform
from pathlib import Path
from typing import Optional, Dict, List

# Check if running on Apple Silicon
IS_APPLE_SILICON = platform.machine() == 'arm64' and platform.system() == 'Darwin'

from PyQt6.QtOpenGLWidgets import QOpenGLWidget
from PyQt6.QtCore import Qt, QTimer, pyqtSlot
from PyQt6.QtGui import QMouseEvent, QSurfaceFormat
from loguru import logger

# Try to import live2d
try:
    import live2d.v3 as live2d
    from live2d.utils.lipsync import WavHandler
    HAS_LIVE2D = True
except ImportError as e:
    HAS_LIVE2D = False
    logger.warning(f"live2d-py not installed: {e}")

# Import TTS Manager for lip sync
try:
    from src.core.tts_manager import TTSManager, get_tts_manager
    HAS_TTS = True
except ImportError:
    HAS_TTS = False
    logger.warning("TTS Manager not available")


class Live2DView(QOpenGLWidget):
    """
    OpenGL widget for rendering Live2D models
    Supports mouse interaction and animation control
    """
    
    # 参数化表情映射表 - 直接操作底层参数，彻底规避 AddExpression 导致的闪退
    EXPRESSION_PARAM_MAP = {
        "happy": "Key17",   # 星星眼
        "sad": "Key20",     # 哭哭
        "angry": "Key14",   # 生气
        "love": "Key32",    # 比心
        "blush": "Key21",   # 红脸
        "daze": "Key15",    # 呆
    }

    def __init__(self, parent=None, model_path: Optional[str] = None):
        super().__init__(parent)

# 🚨 【关键修复 1】：配置 OpenGL 表面，强制分配 8 位的 Alpha 透明通道
        fmt = QSurfaceFormat()
        fmt.setAlphaBufferSize(8)
        self.setFormat(fmt)


# 在 __init__ 中添加：
        self._lip_sync_enabled = False
        self._current_mouth_open = 0.0
        self._mouth_smooth_value = 0.0
        
# 🚨 【关键修复 2】：告诉 Qt 这个 OpenGL 组件允许背景透明
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, False)

        self.model_path = model_path
        self.model = None
        self._live2d_initialized = False
        self._gl_initialized = False
        self._pending_model_path = None

        self.current_expression = "normal"
        self.is_speaking = False

        # Lip sync state
        self._lip_sync_enabled = True
        self._current_mouth_open = 0.0
        self._mouth_smooth_value = 0.0  # Smoothed value for natural movement

        # Touch interaction state
        self._touch_timer = QTimer(self)
        self._touch_timer.setSingleShot(True)
        self._touch_timer.timeout.connect(self._on_touch_end)
        self._expression_before_touch = None

        # Big head mode
        self.is_big_head = False
        self.big_head_y_offset = -1.2  # 调整为对齐头部

        # Mouse tracking
        self.setMouseTracking(True)
        self.mouse_x = 0.0
        self.mouse_y = 0.0

        # Setup update timer
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self._on_update)

        # Setup lip sync update timer (60fps for smooth animation)
        self._lip_sync_timer = QTimer(self)
        self._lip_sync_timer.timeout.connect(self._update_lip_sync)
        self._lip_sync_timer.start(16)  # ~60fps

        # Connect to TTS manager for lip sync
        self._connect_tts_manager()

        logger.info(f"Live2DView created (Apple Silicon: {IS_APPLE_SILICON})")

    def _connect_tts_manager(self):
        """Connect to TTS manager for lip sync signals"""
        if HAS_TTS:
            try:
                tts = get_tts_manager()
                tts.lip_sync_frame.connect(self._on_lip_sync_frame)
                logger.info("✅ Lip sync connected to TTS manager")
            except Exception as e:
                logger.warning(f"Failed to connect TTS manager: {e}")

    @pyqtSlot(float)
    def _on_lip_sync_frame(self, mouth_open: float):
        """Receive lip sync value from TTS manager (0.0 - 1.0)"""
        self._current_mouth_open = mouth_open

    def _update_lip_sync(self):
        """Update mouth parameter smoothly"""
        if not self.model or not HAS_LIVE2D:
            return

        # Smooth the mouth opening value for natural movement
        smoothing_factor = 0.3
        self._mouth_smooth_value += (self._current_mouth_open - self._mouth_smooth_value) * smoothing_factor

        # Map to Live2D mouth open parameter (ParamMouthOpenY typically ranges 0.0 to 1.0)
        try:
            self.model.SetParameterValue("ParamMouthOpenY", self._mouth_smooth_value)
        except Exception as e:
            logger.debug(f"Failed to set mouth parameter: {e}")

    def set_lip_sync_enabled(self, enabled: bool):
        """Enable or disable lip sync"""
        self._lip_sync_enabled = enabled
        if not enabled:
            self._current_mouth_open = 0.0
            self._mouth_smooth_value = 0.0
        logger.info(f"🎭 Lip sync {'enabled' if enabled else 'disabled'}")
    
    def resizeGL(self, w: int, h: int):
        """
        处理视口大小改变，更新投影矩阵，防止模型被拉伸或压缩
        """
        # 确保 OpenGL 上下文和 Live2D 已初始化
        if not self._gl_initialized or not HAS_LIVE2D:
            return
            
        try:
            self.makeCurrent()
            # 告诉 Live2D 模型当前的画布尺寸，它会自动重新计算正确的宽高比（Aspect Ratio）
            if self.model:
                self.model.Resize(w, h)
                logger.info(f"📐 Resized Live2D viewport to {w}x{h}")
        except Exception as e:
            logger.error(f"❌ Failed to resize Live2D viewport: {e}")
            
    def initializeGL(self):
        super().initializeGL()
        
        self._gl_initialized = True
        
        if not HAS_LIVE2D:
            return
        
        try:
            self.makeCurrent()
            live2d.glInit()
            live2d.init()
            self._live2d_initialized = True
            logger.info("✅ Live2D SDK initialized successfully")
            
            if self._pending_model_path:
                self._do_load_model(self._pending_model_path)
                self._pending_model_path = None
        except Exception as e:
            logger.error(f"❌ Failed to initialize Live2D: {e}")
    
    def load_model(self, model_path: str) -> bool:
        if not HAS_LIVE2D:
            return False
        
        if not self._gl_initialized or not self._live2d_initialized:
            self._pending_model_path = model_path
            QTimer.singleShot(100, self._try_load_pending_model)
            return True
        
        return self._do_load_model(model_path)
    
    def _try_load_pending_model(self):
        if self._pending_model_path and self._gl_initialized and self._live2d_initialized:
            self._do_load_model(self._pending_model_path)
            self._pending_model_path = None
    
    def _do_load_model(self, model_path: str) -> bool:
        try:
            self.makeCurrent()
            self.model = live2d.LAppModel()
            model_dir = Path(model_path)
            
            model_json = None
            all_json_files = list(model_dir.glob("*.model3.json"))
            for f in all_json_files:
                model_json = f
                break
            
            if not model_json:
                return False
            
            self.model.LoadModelJson(str(model_json))
            self.model_path = model_path
            logger.info(f"✅ Model loaded successfully: {model_json.name}")
            
            if not self.update_timer.isActive():
                self.update_timer.start(16)
            
            return True
        except Exception as e:
            logger.error(f"❌ Failed to load model: {e}")
            return False
    
    def set_big_head_mode(self, enabled: bool):
        self.is_big_head = enabled
        if self.model and HAS_LIVE2D:
            if enabled:
                self.model.SetScale(2.5)
                self.model.SetOffset(0.0, -1.2)
            else:
                self.model.SetScale(1.0)
                self.model.SetOffset(0.0, 0.0)
        self.update()

    def paintGL(self):
        if not self.model or not HAS_LIVE2D:
            return

        try:
            self.makeCurrent()

# 🚨 【关键修复 3】：用完全透明的颜色 (RGBA 都是 0) 清空上一帧的画面
            if hasattr(live2d, 'clearBuffer'):
                live2d.clearBuffer(0.0, 0.0, 0.0, 0.0)
  
# 🚨 【关键插入点】：必须在 model.Update() 之前设置嘴型参数！
            if getattr(self, '_lip_sync_enabled', False):
                self._update_lip_sync()

            self.model.Update()  # Live2D 引擎会在这一步吸收你的嘴型参数并计算物理效果
            
            self.model.Drag(self.mouse_x, self.mouse_y)
          
            # 保持大头模式缩放和偏移
            if self.is_big_head:
                self.model.SetScale(2.5)
                self.model.SetOffset(0.0, -1.2)
            else:
                self.model.SetScale(1.0)
                self.model.SetOffset(0.0, 0.0)

            self.model.Draw()
        except Exception as e:
            logger.error(f"Render error: {e}")
    
    def _on_update(self):
        self.update()
    
    def set_expression(self, name: str) -> bool:
        """
        使用参数化方式设置表情，彻底规避闪退风险
        """
        if not self.model or not HAS_LIVE2D:
            return False
        
        logger.info(f"Setting expression (Param-based): {name}")
        
        try:
            # 1. 重置所有表情参数为 0.0
            for param in self.EXPRESSION_PARAM_MAP.values():
                self.model.SetParameterValue(param, 0.0)
            
            # 2. 如果是正常模式，到此为止
            if name in ["normal", "reset"]:
                self.current_expression = "normal"
                return True
                
            # 3. 设置目标表情参数
            param_id = self.EXPRESSION_PARAM_MAP.get(name.lower())
            if param_id:
                self.model.SetParameterValue(param_id, 1.0)
                self.current_expression = name
                logger.info(f"✅ Expression set via parameter: {name} ({param_id}=1.0)")
                return True
            else:
                logger.warning(f"Unknown expression name: {name}")
                return False
        except Exception as e:
            logger.error(f"Failed to set param-based expression: {e}")
            return False
    
    def set_parameter(self, param_id: str, value: float) -> bool:
        if not self.model or not HAS_LIVE2D:
            return False
        try:
            self.model.SetParameterValue(param_id, value)
            return True
        except Exception as e:
            logger.error(f"Failed to set parameter {param_id}: {e}")
            return False
    
    def get_parameter(self, param_id: str) -> float:
        """
        获取 Live2D 模型参数值
        """
        if not self.model or not HAS_LIVE2D:
            return 0.0
        
        try:
            return self.model.GetParameterValue(param_id)
        except:
            return 0.0
    
    def list_parameters(self, pattern: str = None) -> list:
        """
        列出所有可用参数
        """
        if not self.model or not HAS_LIVE2D:
            return []
        
        try:
            param_count = self.model.GetParameterCount()
            param_ids = []
            
            for i in range(param_count):
                try:
                    param_id = self.model.GetParamIds()[i]
                    if pattern is None or pattern.lower() in str(param_id).lower():
                        param_ids.append(str(param_id))
                except:
                    pass
            
            return param_ids
        except Exception as e:
            logger.error(f"Failed to list parameters: {e}")
            return []
    

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton and self.model:
            # 触发摸脸效果
            self.set_parameter("Key39", 1.0)
            self._touch_timer.start(1500)
            logger.info("👆 Touch interaction: 摸脸 triggered (Key39=1.0)")
        super().mousePressEvent(event)
    
    def _on_touch_end(self):
        if self.model:
            self.set_parameter("Key39", 0.0)
            logger.info("👋 Touch interaction ended")
    
    def cleanup(self):
        self.update_timer.stop()
        self._lip_sync_timer.stop()
        if HAS_LIVE2D and self._live2d_initialized:
            try:
                live2d.dispose()
                self._live2d_initialized = False
            except:
                pass
