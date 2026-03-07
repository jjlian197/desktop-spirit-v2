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
import sys
import json
import urllib.request
import urllib.error
from pathlib import Path
from typing import Optional, Dict, List

# Check if running on Apple Silicon
IS_APPLE_SILICON = platform.machine() == 'arm64' and platform.system() == 'Darwin'

# Brain HTTP API 配置
BRAIN_HTTP_PORT = 8766
BRAIN_HTTP_HOST = "127.0.0.1"


def get_project_dir() -> str:
    """
    💜 获取项目根目录（支持 .app 包、PyInstaller 和普通运行）
    无论从哪里启动，都能找到正确的资源路径
    """
    # 🚨 检查是否是 PyInstaller 打包后的环境
    if hasattr(sys, '_MEIPASS'):
        # PyInstaller 会将资源解压到 sys._MEIPASS 临时目录
        return sys._MEIPASS
    
    # 获取当前文件路径
    current_file = os.path.abspath(__file__)
    # src/core/live2d_view.py -> 项目根目录
    project_dir = os.path.dirname(os.path.dirname(os.path.dirname(current_file)))
    
    # 检查是否在 .app 包内运行
    if ".app/Contents/" in project_dir:
        # 在 .app 包内，找到 .app 的父目录
        # /path/to/雪莉.app/Contents/Resources/... -> /path/to
        app_path = project_dir
        while app_path and not app_path.endswith(".app"):
            app_path = os.path.dirname(app_path)
        if app_path:
            # .app 同级目录应该有 src/assets
            sibling_dir = os.path.dirname(app_path)
            # 检查是否是项目目录
            if os.path.exists(os.path.join(sibling_dir, "src", "assets")):
                return sibling_dir
    
    return project_dir

from PyQt6.QtOpenGLWidgets import QOpenGLWidget
from PyQt6.QtCore import Qt, QTimer, pyqtSlot, pyqtSignal, QThread
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
    # 🚨 【好感度解锁表情】只有这些参数是模型中实际存在的
    # 注意：对于复合表情（需要设置多个参数），使用列表格式 [("param", value), ...]
    EXPRESSION_PARAM_MAP = {
        "happy": [("ParamEyeLSmile", 1.0), ("ParamEyeRSmile", 1.0)],  # 微笑（眼睛弯弯）
        "sad": "Key20",         # 哭哭
        "angry": "Key14",       # 生气 (<30好感度)
        "love": "Key32",        # 比心 (>80好感度)
        "blush": "Key21",       # 红脸 (30-60好感度)
        "daze": "Key15",        # 呆 (30-60好感度)
        # 🚨 新增解锁表情（复用已有参数）
        "star_eye": "Key17",    # 星星眼 (60-80好感度)
        "cat_paw": "Key32",     # 猫爪 (60-80好感度)
        "heart": "Key32",       # 比心 (>80好感度)
        "cat_mouth": "Key32",   # 叼猫条 (>80好感度)
        "q_style": "Key17",     # 变Q (>80好感度)
        "surprised": "Key14",   # 惊讶
        "sleepy": "Key15",      # 困倦
        # 注意：normal 不在此映射中，单独处理
    }
    
    # 英文到中文的映射（供外部使用）
    # 🚨 【好感度解锁表情映射】
    _expression_mapping = {
        "happy": "happy",
        "sad": "sad",
        "angry": "angry",
        "love": "love",
        "blush": "blush",
        "daze": "daze",
        "normal": "normal",
        "surprised": "surprised",
        "sleepy": "sleepy",
        # 🚨 新增好感度解锁表情
        "star_eye": "happy",      # 星星眼 → happy
        "cat_paw": "love",        # 猫爪 → love  
        "heart": "love",          # 比心 → love
        "cat_mouth": "love",      # 叼猫条 → love
        "q_style": "happy",       # 变Q → happy
        "sleepy": "sleepy",
        # 🚨 新增解锁表情
        "star_eye": "星星眼",
        "cat_paw": "猫爪",
        "heart": "比心",
        "cat_mouth": "叼猫条",
        "q_style": "变Q",
    }
    
    # Signal emitted when model is successfully loaded
    model_loaded = pyqtSignal()
    
    # 🚨 【触觉反馈】触摸事件信号 - 当主人触摸雪莉时发射
    touched = pyqtSignal(str, str)  # (action, part) 例如 ("tap", "head")

    def __init__(self, parent=None, model_path: Optional[str] = None):
        super().__init__(parent)

        # 🚨 【关键修复 1】：配置 OpenGL 表面，强制分配 8 位的 Alpha 透明通道
        fmt = QSurfaceFormat()
        fmt.setAlphaBufferSize(8)
        self.setFormat(fmt)
        
        # 🚨 【关键修复 2】：告诉 Qt 这个 OpenGL 组件允许背景透明
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, False)

        self.model_path = model_path
        self.model = None
        self._live2d_initialized = False
        self._gl_initialized = False
        self._pending_model_path = None
        self._is_model_loaded = False  # 💜 明确标记模型是否成功加载

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
        
        # 🚨 鼠标跟随开关
        self._mouse_follow_enabled = True
        
        # 🚨 动作播放状态（用于暂停鼠标跟随）
        self._motion_playing = False
        self._current_motion_group = None
        
        # 🚨 TTS 说话状态（用于回正）
        self._tts_speaking = False

        # Setup update timer
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self._on_update)

        # Setup lip sync update timer (60fps for smooth animation)
        self._lip_sync_timer = QTimer(self)
        self._lip_sync_timer.timeout.connect(self._update_lip_sync)
        self._lip_sync_timer.start(16)  # ~60fps
        
        # 🚨 动作状态检查定时器（用于检测非 Idle 动作是否播放完成）
        self._motion_check_timer = QTimer(self)
        self._motion_check_timer.timeout.connect(self._check_motion_finished)
        self._motion_check_timer.start(100)  # 100ms 检查一次

        # Connect to TTS manager for lip sync
        self._connect_tts_manager()

        logger.info(f"Live2DView created (Apple Silicon: {IS_APPLE_SILICON})")

    def _connect_tts_manager(self):
        """Connect to TTS manager for lip sync signals"""
        if HAS_TTS:
            try:
                tts = get_tts_manager()
                tts.lip_sync_frame.connect(self._on_lip_sync_frame)
                # 🚨 连接 TTS 开始/结束信号
                tts.tts_started.connect(self._on_tts_started)
                tts.tts_finished.connect(self._on_tts_finished)
                logger.info("✅ Lip sync connected to TTS manager")
            except Exception as e:
                logger.warning(f"Failed to connect TTS manager: {e}")
    
    def _on_tts_started(self, text: str):
        """TTS 开始说话时触发 - 设置回正状态"""
        logger.info("🎙️ TTS started, resetting to center position")
        self._tts_speaking = True
        # 发送回正参数给大脑
        self._reset_to_center()
    
    def _on_tts_finished(self):
        """TTS 说话结束时触发"""
        logger.info("🎙️ TTS finished, resuming normal tracking")
        self._tts_speaking = False
    
    def _get_offset_values(self) -> Dict[str, float]:
        """从 Brain HTTP API 获取鼠标跟随的偏移值"""
        try:
            req = urllib.request.Request(
                f"http://{BRAIN_HTTP_HOST}:{BRAIN_HTTP_PORT}/health",
                method='GET'
            )
            with urllib.request.urlopen(req, timeout=1) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode('utf-8'))
                    # 从 health 端点获取 mouse_config 中的偏移值
                    # 如果 API 支持，可以直接获取完整的 mouse_config
                    # 这里使用默认值作为后备
                    return {
                        "offset_angle_x": data.get("mouse_offset_angle_x", 25.0),
                        "offset_angle_y": data.get("mouse_offset_angle_y", -30.0),
                        "offset_angle_z": data.get("mouse_offset_angle_z", -30.0),
                        "offset_body_x": data.get("mouse_offset_body_x", 15.0),
                        "offset_eye_x": data.get("mouse_offset_eye_x", 0.5),
                        "offset_eye_y": data.get("mouse_offset_eye_y", 0.0),
                    }
        except Exception as e:
            logger.debug(f"Failed to get offset values from brain: {e}")
        
        # 返回默认值
        return {
            "offset_angle_x": 25.0,
            "offset_angle_y": -30.0,
            "offset_angle_z": -30.0,
            "offset_body_x": 15.0,
            "offset_eye_x": 0.5,
            "offset_eye_y": 0.0,
        }
    
    def _reset_to_center(self):
        """发送回正参数（从 brain 获取偏移值）"""
        if not self.model or not HAS_LIVE2D:
            return
        
        # 🚨 从 brain 获取偏移值
        offsets = self._get_offset_values()
        
        center_params = {
            "ParamAngleX": offsets["offset_angle_x"],
            "ParamAngleY": offsets["offset_angle_y"],
            "ParamAngleZ": offsets["offset_angle_z"],
            "ParamBodyAngleX": offsets["offset_body_x"],
            "ParamBodyAngleY": 0.0,
            "ParamBodyAngleZ": 0.0,
            "ParamEyeBallX": offsets["offset_eye_x"],
            "ParamEyeBallY": offsets["offset_eye_y"],
        }
        try:
            for param_id, value in center_params.items():
                self.model.SetParameterValue(param_id, value)
            logger.debug(f"✅ Center position reset with offsets from brain: X={offsets['offset_angle_x']}, Y={offsets['offset_angle_y']}")
        except Exception as e:
            logger.debug(f"Failed to reset center position: {e}")
    
    def set_mouse_follow_enabled(self, enabled: bool):
        """设置鼠标跟随开关"""
        self._mouse_follow_enabled = enabled
        logger.info(f"🖱️ Mouse follow {'enabled' if enabled else 'disabled'}")
        # 如果禁用，发送回正参数
        if not enabled:
            self._reset_to_center()
    
    def is_mouse_follow_enabled(self) -> bool:
        """获取鼠标跟随状态"""
        return self._mouse_follow_enabled
    
    def is_motion_playing(self) -> bool:
        """检查是否正在播放非 Idle 动作"""
        return self._motion_playing
    
    def is_tts_speaking(self) -> bool:
        """检查是否正在说话"""
        return self._tts_speaking
    
    def should_pause_mouse_follow(self) -> bool:
        """检查是否应该暂停鼠标跟随"""
        # 暂停条件：1. 鼠标跟随被禁用 2. 正在播放非 Idle 动作 3. 正在说话
        if not self._mouse_follow_enabled:
            return True
        if self._tts_speaking:
            return True
        if self._motion_playing and self._current_motion_group and self._current_motion_group.lower() != "idle":
            return True
        return False
    
    def _check_motion_finished(self):
        """检查非 Idle 动作是否播放完成"""
        if not self._motion_playing or not self.model or not HAS_LIVE2D:
            return
        
        try:
            # 使用 IsMotionFinished 检查动作是否完成
            if hasattr(self.model, 'IsMotionFinished') and self.model.IsMotionFinished():
                logger.info(f"🎬 Motion finished: {self._current_motion_group}, resuming mouse follow")
                self._motion_playing = False
                self._current_motion_group = None
        except Exception as e:
            logger.debug(f"Failed to check motion status: {e}")

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
        logger.info("🎨 OpenGL initializeGL called")
        super().initializeGL()
        
        self._gl_initialized = True
        logger.info("✅ OpenGL context initialized")
        
        if not HAS_LIVE2D:
            logger.warning("⚠️ Live2D not available, skipping SDK initialization")
            return
        
        try:
            self.makeCurrent()
            logger.info("🚀 Initializing Live2D SDK...")
            live2d.glInit()
            live2d.init()
            self._live2d_initialized = True
            logger.info("✅ Live2D SDK initialized successfully")
            
            if self._pending_model_path:
                logger.info(f"📦 Loading pending model: {self._pending_model_path}")
                self._do_load_model(self._pending_model_path)
                self._pending_model_path = None
        except Exception as e:
            logger.error(f"❌ Failed to initialize Live2D: {e}")
            import traceback
            traceback.print_exc()
    
    def load_model(self, model_path: str) -> bool:
        if not HAS_LIVE2D:
            return False
        
        if not self._gl_initialized or not self._live2d_initialized:
            self._pending_model_path = model_path
            QTimer.singleShot(100, self._try_load_pending_model)
            return True
        
        return self._do_load_model(model_path)
    
    def _try_load_pending_model(self):
        if not self._pending_model_path:
            return
        
        if self._gl_initialized and self._live2d_initialized:
            # 条件满足，加载模型
            success = self._do_load_model(self._pending_model_path)
            if success:
                self._pending_model_path = None
            else:
                # 加载失败，稍后重试
                logger.warning("⚠️ Model load failed, will retry...")
                QTimer.singleShot(500, self._try_load_pending_model)
        else:
            # 条件不满足，稍后重试
            logger.debug("⏳ Waiting for OpenGL/Live2D initialization...")
            QTimer.singleShot(100, self._try_load_pending_model)
    
    def _do_load_model(self, model_path: str) -> bool:
        # 💜 重置模型加载状态
        self._is_model_loaded = False
        
        # 💜 检查 live2d 是否可用
        if not HAS_LIVE2D or live2d is None:
            logger.error("❌ Live2D not available")
            return False
        
        # 💜 检查 OpenGL 和 Live2D 是否已初始化
        if not self._gl_initialized:
            logger.error("❌ OpenGL not initialized")
            return False
        
        if not self._live2d_initialized:
            logger.error("❌ Live2D SDK not initialized")
            return False
        
        # 💜 先重置模型，避免残留无效对象
        self.model = None
        
        try:
            self.makeCurrent()
            
            model_dir = Path(model_path)
            
            # 💜 检查模型目录是否存在
            if not model_dir.exists():
                logger.error(f"❌ Model directory does not exist: {model_dir}")
                return False
            
            logger.info(f"📁 Loading model from: {model_dir.absolute()}")
            
            model_json = None
            all_json_files = list(model_dir.glob("*.model3.json"))
            for f in all_json_files:
                model_json = f
                break
            
            if not model_json:
                logger.error(f"❌ No .model3.json file found in {model_dir}")
                return False
            
            logger.info(f"📄 Found model JSON: {model_json.name}")
            
            # 💜 先创建模型对象，成功后才会赋值给 self.model
            logger.info("🔧 Creating LAppModel...")
            model = live2d.LAppModel()
            if model is None:
                logger.error("❌ LAppModel() returned None")
                return False
            logger.info(f"✅ LAppModel created: {type(model)}")
            
            # 🚨 加载模型
            model_json_str = str(model_json.absolute())
            logger.info(f"📂 Loading model with path: {model_json_str}")
            model.LoadModelJson(model_json_str)
            
            # 🚨 调用 Update 来初始化模型状态（可能对动作加载很重要）
            try:
                model.Update(0)  # 使用 0 时间间隔进行初始化更新
                logger.info("✅ Initial model Update called")
            except Exception as e:
                logger.debug(f"Initial Update error (may be normal): {e}")
            
            self.model_path = model_path
            
            # 💜 成功后才赋值给 self.model
            self.model = model
            
            # 🚨 立即检查 motion groups（调试用）
            try:
                if hasattr(self.model, 'GetMotionGroups'):
                    groups = self.model.GetMotionGroups()
                    logger.info(f"📋 Motion groups after LoadModelJson: {groups}")
                if hasattr(self.model, 'GetMotions'):
                    motions = self.model.GetMotions()
                    logger.info(f"📋 Motions after LoadModelJson: {motions}")
                if hasattr(self.model, 'GetModelHomeDir'):
                    home_dir = self.model.GetModelHomeDir()
                    logger.info(f"📋 Model home dir: {home_dir}")
            except Exception as e:
                logger.debug(f"Could not get motion info: {e}")
            
            # 🚨 预加载动作文件
            self._preload_motions(model_dir)
            
            logger.info(f"✅ Model loaded successfully: {model_json.name}")
            self._is_model_loaded = True  # 💜 标记模型加载成功
            
            if not self.update_timer.isActive():
                self.update_timer.start(16)
            
            # Emit signal to notify that model is ready
            self.model_loaded.emit()
            
            return True
        except Exception as e:
            logger.error(f"❌ Failed to load model: {e}")
            self.model = None  # 💜 确保失败时模型为 None
            self._is_model_loaded = False  # 💜 标记模型加载失败
            return False
    
    def _preload_motions(self, model_dir: Path):
        """预加载动作文件到模型 - 检查动作是否正确加载"""
        if not self.model or not HAS_LIVE2D:
            return
        
        logger.info("🔍 Checking motion groups after model load...")
        
        # 检查当前已加载的 motion groups
        try:
            if hasattr(self.model, 'GetMotionGroups'):
                groups = self.model.GetMotionGroups()
                logger.info(f"📋 Motion groups: {groups}")
            if hasattr(self.model, 'GetMotions'):
                motions = self.model.GetMotions()
                logger.info(f"📋 Motions: {motions}")
        except Exception as e:
            logger.debug(f"Could not get motion info: {e}")
    

    
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
        if not HAS_LIVE2D:
            return

        try:
            from OpenGL.GL import (
                glEnable, GL_BLEND, glBlendFunc, GL_ONE, GL_ONE_MINUS_SRC_ALPHA,
                glClearColor, glClear, GL_COLOR_BUFFER_BIT, GL_DEPTH_BUFFER_BIT
            )
            from OpenGL.error import GLError
            
            # 🚨 【关键】清除背景
            # 使用很小的非零 alpha 值避免某些 OpenGL 驱动报错
            try:
                glClearColor(0.0, 0.0, 0.0, 0.01)  # 接近透明的黑色
                glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
            except GLError:
                # 如果失败，使用完全不透明黑色
                try:
                    glClearColor(0.0, 0.0, 0.0, 1.0)
                    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
                except:
                    pass  # 忽略 OpenGL 错误
            
            # 💜 如果模型未加载成功，直接返回
            if not self._is_model_loaded or not self.model:
                return
            
            # 启用 premultiplied alpha 混合
            glEnable(GL_BLEND)
            glBlendFunc(GL_ONE, GL_ONE_MINUS_SRC_ALPHA)
  
            # 嘴型同步
            if getattr(self, '_lip_sync_enabled', False):
                self._update_lip_sync()

            self.model.Update()
            self.model.Drag(self.mouse_x, self.mouse_y)
          
            # 大头模式
            if self.is_big_head:
                self.model.SetScale(2.5)
                self.model.SetOffset(0.0, -1.2)
            else:
                self.model.SetScale(1.0)
                self.model.SetOffset(0.0, 0.0)

            # 绘制模型
            self.model.Draw()
            
        except Exception as e:
            logger.error(f"Render error: {e}")
    
    def _on_update(self):
        self.update()
    
    def set_expression(self, name: str) -> bool:
        """
        使用参数化方式设置表情，彻底规避闪退风险
        支持简单参数（str）和复合参数（list of tuples）
        """
        if not self.model or not HAS_LIVE2D:
            return False
        
        logger.info(f"Setting expression (Param-based): {name}")
        
        try:
            # 1. 重置所有表情参数为 0.0
            for param_def in self.EXPRESSION_PARAM_MAP.values():
                if isinstance(param_def, str):
                    # 简单参数
                    self.model.SetParameterValue(param_def, 0.0)
                elif isinstance(param_def, list):
                    # 复合参数 - 重置所有相关参数
                    for param_id, _ in param_def:
                        self.model.SetParameterValue(param_id, 0.0)
            
            # 2. 如果是正常模式，到此为止
            if name in ["normal", "reset"]:
                self.current_expression = "normal"
                return True
                
            # 3. 设置目标表情参数
            param_def = self.EXPRESSION_PARAM_MAP.get(name.lower())
            if param_def is None:
                # normal 模式，已经重置过参数了
                self.current_expression = name
                logger.info(f"✅ Expression set: {name} (normal mode)")
                return True
            elif isinstance(param_def, str):
                # 简单参数
                try:
                    self.model.SetParameterValue(param_def, 1.0)
                    self.current_expression = name
                    logger.info(f"✅ Expression set via parameter: {name} ({param_def}=1.0)")
                    return True
                except Exception as e:
                    logger.error(f"Failed to set parameter {param_def}: {e}")
                    return False
            elif isinstance(param_def, list):
                # 复合参数 - 设置多个参数
                try:
                    for param_id, value in param_def:
                        self.model.SetParameterValue(param_id, value)
                    self.current_expression = name
                    param_names = ", ".join([p[0] for p in param_def])
                    logger.info(f"✅ Expression set via parameters: {name} ({param_names})")
                    return True
                except Exception as e:
                    logger.error(f"Failed to set composite expression {name}: {e}")
                    return False
            else:
                logger.warning(f"Unknown expression name: {name}")
                return False
        except Exception as e:
            logger.error(f"Failed to set param-based expression: {e}")
            return False
    
    def get_available_expressions(self) -> list:
        """返回所有可用表情列表"""
        return ["normal"] + list(self.EXPRESSION_PARAM_MAP.keys())
    
    def find_expression(self, name: str) -> str:
        """查找表情名称，支持大小写不敏感匹配"""
        if not name:
            return "normal"
        name_lower = name.lower()
        if name_lower in ["normal", "reset"]:
            return "normal"
        if name_lower in self.EXPRESSION_PARAM_MAP:
            return name_lower
        return None
    
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
    
    def trigger_motion(self, group: str, index: int = 0):
        """🚨 【触觉反馈】触发动画/动作 - 使用原生 StartMotion"""
        if not self.model or not HAS_LIVE2D:
            logger.warning("Cannot trigger motion: model not loaded")
            return False
        
        # 🚨 更新动作播放状态
        is_idle = group.lower() == "idle"
        self._current_motion_group = group
        
        # 🚨 非 Idle 动画播放时标记为正在播放
        if not is_idle:
            self._motion_playing = True
            logger.info(f"🎬 Non-idle motion started: {group}, mouse follow paused")
        
        # 🚨 如果 motion groups 为空，尝试手动加载动作
        model_dir = Path(self.model_path) if self.model_path else None
        if model_dir:
            motion_file = model_dir / f"{group}.motion3.json"
            if motion_file.exists():
                logger.info(f"📂 Found motion file: {motion_file}")
                # 尝试使用 LoadExtraMotion 如果存在
                if hasattr(self.model, 'LoadExtraMotion'):
                    try:
                        result = self.model.LoadExtraMotion(group, str(motion_file.absolute()))
                        logger.info(f"✅ LoadExtraMotion result: {result}")
                    except Exception as e:
                        logger.error(f"❌ LoadExtraMotion failed: {e}")
        
        # 🚨 尝试使用 StartRandomMotion 作为备选
        try:
            priority = live2d.MotionPriority.FORCE
            logger.info(f"🎬 Trying StartMotion: {group} index {index} (priority={priority})...")
            
            # 首先尝试 StartMotion
            # 🚨 StartMotion 返回 None 是正常行为（void 函数），不代表失败
            self.model.StartMotion(group, index, priority)
            logger.info(f"✅ Motion started: {group} index {index}")
            return True
                
        except Exception as e:
            logger.error(f"❌ Motion trigger failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            # 失败时重置状态
            if not is_idle:
                self._motion_playing = False
            return False
    

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton and self.model:
            # 🚨 【触觉反馈 - 第一步】获取点击位置并检测碰撞区域
            x = event.position().x()
            y = event.position().y()
            
            # 检测点击区域（基于屏幕坐标比例）
            width = self.width()
            height = self.height()
            
            # 归一化坐标 (0-1)
            nx = x / width
            ny = y / height
            
            # 🚨 【分区触摸反馈】精细的区域检测
            # 头顶区域：最上方 0.15-0.35
            if 0.35 <= nx <= 0.65 and 0.15 <= ny <= 0.30:
                touched_part = "头顶"
                logger.info(f"👆 主人抚摸了雪莉的头顶！坐标: ({nx:.2f}, {ny:.2f})")
            # 脸颊/脸部区域：中间偏上 0.30-0.45
            elif 0.30 <= nx <= 0.70 and 0.30 <= ny <= 0.45:
                touched_part = "脸颊"
                logger.info(f"👆 主人捏了雪莉的脸！坐标: ({nx:.2f}, {ny:.2f})")
            # 左耳区域
            elif nx < 0.30 and 0.25 <= ny <= 0.40:
                touched_part = "左耳"
                logger.info(f"👆 主人摸了雪莉的左耳！坐标: ({nx:.2f}, {ny:.2f})")
            # 右耳区域
            elif nx > 0.70 and 0.25 <= ny <= 0.40:
                touched_part = "右耳"
                logger.info(f"👆 主人摸了雪莉的右耳！坐标: ({nx:.2f}, {ny:.2f})")
            # 身体/衣服区域：中间 0.45-0.70
            elif 0.30 <= nx <= 0.70 and 0.45 <= ny <= 0.70:
                touched_part = "身体"
                logger.info(f"👆 主人抱了雪莉！坐标: ({nx:.2f}, {ny:.2f})")
            # 左手/左爪区域
            elif nx < 0.25 and 0.55 <= ny <= 0.75:
                touched_part = "左手"
                logger.info(f"👆 主人握了雪莉的左手！坐标: ({nx:.2f}, {ny:.2f})")
            # 右手/右爪区域
            elif nx > 0.75 and 0.55 <= ny <= 0.75:
                touched_part = "右手"
                logger.info(f"👆 主人握了雪莉的右手！坐标: ({nx:.2f}, {ny:.2f})")
            # 尾巴区域：下方
            elif 0.40 <= nx <= 0.60 and ny > 0.70:
                touched_part = "尾巴"
                logger.info(f"👆 主人摸了雪莉的尾巴！坐标: ({nx:.2f}, {ny:.2f})")
            else:
                touched_part = "身体"
                logger.info(f"👆 主人触摸了雪莉！坐标: ({nx:.2f}, {ny:.2f})")
            
            # 发射触摸信号（通知 SpriteWindow）
            self.touched.emit("tap", touched_part)
            
            # 本地即时反馈：根据部位显示不同表情
            if touched_part in ["脸颊", "左耳", "右耳"]:
                self.set_expression("blush")  # 脸红
            elif touched_part in ["头顶"]:
                self.set_expression("happy")  # 开心
            elif touched_part in ["左手", "右手"]:
                self.set_expression("love")  # 爱心眼
            
            # 触发摸脸效果（本地即时反馈）
            self.set_parameter("Key39", 1.0)
            self._touch_timer.start(1500)
        
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
