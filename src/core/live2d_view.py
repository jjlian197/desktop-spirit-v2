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
IS_WINDOWS = platform.system() == 'Windows'

# Windows API for global mouse tracking
if IS_WINDOWS:
    import ctypes
    from ctypes import wintypes
    
    class POINT(ctypes.Structure):
        _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]
    
    def get_global_mouse_pos():
        """Get global mouse position using Windows API"""
        pt = POINT()
        ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
        return pt.x, pt.y
else:
    def get_global_mouse_pos():
        """Dummy function for non-Windows platforms"""
        return 0, 0

from PyQt6.QtOpenGLWidgets import QOpenGLWidget
from PyQt6.QtCore import Qt, QTimer, pyqtSlot, pyqtSignal
from PyQt6.QtGui import QMouseEvent, QSurfaceFormat
from loguru import logger

# Try to import live2d
try:
    import live2d.v3 as live2d
    from live2d.utils.lipsync import WavHandler
    HAS_LIVE2D = True
    logger.info(f"✅ live2d imported successfully: {live2d}")
except ImportError as e:
    HAS_LIVE2D = False
    logger.error(f"❌ live2d-py import failed: {e}")
    import traceback
    logger.error(traceback.format_exc())

# Import TTS Manager for lip sync
try:
    from src.core.tts_manager import TTSManager, get_tts_manager
    HAS_TTS = True
except ImportError:
    HAS_TTS = False
    logger.warning("TTS Manager not available")

# Import MotionPlayer
try:
    from src.core.motion_player import MotionPlayer
    HAS_MOTION_PLAYER = True
except ImportError:
    HAS_MOTION_PLAYER = False
    logger.warning("MotionPlayer not available")


class Live2DView(QOpenGLWidget):
    """
    OpenGL widget for rendering Live2D models
    Supports mouse interaction and animation control
    """
    
    # 🚨 【触觉反馈】触摸事件信号 - 当用户触摸雪莉时发射 (action, part)
    touched = pyqtSignal(str, str)
    # 模型加载完成信号
    model_loaded = pyqtSignal()
    
    # 参数化表情映射表 - 直接操作底层参数，彻底规避 AddExpression 导致的闪退
    EXPRESSION_PARAM_MAP = {
        "happy": "Key17",   # 星星眼
        "sad": "Key20",     # 哭哭
        "angry": "Key14",   # 生气
        "love": "Key32",    # 比心
        "blush": "Key21",   # 红脸
        "daze": "Key15",    # 呆
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
        # 新增好感度解锁表情
        "star_eye": "happy",      # 星星眼 -> happy
        "cat_paw": "happy",       # 猫爪 -> happy
        "heart": "love",          # 比心 -> love
        "cat_mouth": "love",      # 叼猫条 -> love
        "q_style": "happy",       # 变Q -> happy
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
        self._temp_model_json = None  # 🚨 临时 model.json 文件路径

        # 🚨 MotionPlayer 作为动作播放的备选方案
        self._motion_player = None
        self._motion_files: Dict[str, Path] = {}

        # 🚨 动作播放状态（用于暂停鼠标跟随）
        self._motion_playing = False
        self._motion_playing_timer = QTimer(self)
        self._motion_playing_timer.timeout.connect(self._check_motion_finished)

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
        
        # Eye tracking (视线跟随)
        self._eye_tracking_enabled = True  # 默认开启
        self._eye_tracking_timer = QTimer(self)
        self._eye_tracking_timer.timeout.connect(self._update_eye_tracking)
        self._eye_tracking_timer.start(50)  # 20fps 更新视线

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
            logger.info(f"🔧 _do_load_model started: {model_path}")
            self.makeCurrent()
            logger.debug("✅ OpenGL context made current")
            
            self.model = live2d.LAppModel()
            logger.debug("✅ LAppModel created")
            
            model_dir = Path(model_path)
            logger.debug(f"📂 Model dir: {model_dir}, exists: {model_dir.exists()}")
            
            model_json = None
            all_json_files = list(model_dir.glob("*.model3.json"))
            logger.debug(f"📄 Found {len(all_json_files)} .model3.json files: {all_json_files}")
            
            for f in all_json_files:
                model_json = f
                break
            
            if not model_json:
                logger.error(f"❌ No model3.json found in {model_dir}")
                return False
            
            logger.info(f"📄 Using model json: {model_json}")
            
            # 🚨 【关键】先修改 model3.json 添加动作组映射
            modified_model_json = self._prepare_model_json_with_motions(model_dir, model_json)
            self._temp_model_json = modified_model_json  # 保存路径供清理使用
            
            logger.info(f"📄 Loading modified model json: {modified_model_json}")
            self.model.LoadModelJson(str(modified_model_json))
            self.model_path = model_path
            logger.info(f"✅ Model loaded successfully: {model_json.name}")
            
            # 🚨 预加载动作文件
            self._preload_motions(model_dir)
            
            if not self.update_timer.isActive():
                self.update_timer.start(16)
            
            # 🚨 发射模型加载完成信号
            self.model_loaded.emit()
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to load model: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    def _prepare_model_json_with_motions(self, model_dir: Path, original_json: Path) -> Path:
        """
        🚨 动态修改 model3.json 添加动作组映射
        - Tap -> 摸摸头.motion3.json
        - Idle -> 待机动画.motion3.json
        返回修改后的临时文件路径（放在模型目录中）
        """
        try:
            import json
            
            # 读取原始 model3.json
            with open(original_json, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 确保 FileReferences 存在
            if 'FileReferences' not in data:
                data['FileReferences'] = {}
            
            # 确保 Motions 存在
            if 'Motions' not in data['FileReferences']:
                data['FileReferences']['Motions'] = {}
            
            motions = data['FileReferences']['Motions']
            
            # 定义动作映射（使用英文文件名避免编码问题）
            motion_mapping = {
                "Tap": "Tap.motion3.json",
                "Idle": "Idle.motion3.json"
            }
            
            # 添加动作组（如果不存在）
            for group_name, motion_file in motion_mapping.items():
                motion_path = model_dir / motion_file
                if motion_path.exists():
                    if group_name not in motions:
                        motions[group_name] = []
                    # 检查是否已添加
                    already_added = any(m.get('File') == motion_file for m in motions[group_name])
                    if not already_added:
                        motions[group_name].append({"File": motion_file})
                        logger.info(f"✅ 动作组添加: {group_name} -> {motion_file}")
                else:
                    logger.debug(f"动作文件不存在: {motion_path}")
            
            # 🚨 【关键】将临时文件放在模型目录中，保持相对路径正确
            temp_json = model_dir / f"_temp_with_motions_{original_json.name}"
            
            with open(temp_json, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            return temp_json
            
        except Exception as e:
            logger.error(f"❌ 准备 model.json 失败: {e}，使用原始文件")
            return original_json
    
    def _preload_motions(self, model_dir: Path):
        """🚨 预加载动作文件 - 用于 MotionPlayer 备选方案"""
        if not HAS_MOTION_PLAYER:
            return
        
        motion_mapping = {
            "Tap": "Tap.motion3.json",
            "Idle": "Idle.motion3.json"
        }
        
        # 初始化 MotionPlayer
        self._motion_player = MotionPlayer(self._set_motion_param)
        
        for group_name, filename in motion_mapping.items():
            motion_file = model_dir / filename
            if motion_file.exists():
                self._motion_files[group_name] = motion_file
                logger.info(f"✅ Motion registered: {group_name} -> {filename}")
            else:
                logger.warning(f"⚠️ Motion file not found: {motion_file}")
    
    def _set_motion_param(self, param_id: str, value: float):
        """MotionPlayer 的参数设置回调"""
        if self.model and HAS_LIVE2D:
            try:
                self.model.SetParameterValue(param_id, value)
            except Exception as e:
                logger.debug(f"Failed to set motion param {param_id}: {e}")

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

    def _get_eye_tracking_values(self):
        """在 paintGL 中实时计算眼动跟踪值，确保每帧都是最新的"""
        if not self._eye_tracking_enabled:
            return 0.0, 0.0
        
        try:
            from PyQt6.QtCore import QPoint
            
            # 获取窗口位置
            window_pos = self.mapToGlobal(QPoint(0, 0))
            win_x = window_pos.x()
            win_y = window_pos.y()
            win_w = self.width()
            win_h = self.height()
            
            # 计算窗口中心
            center_x = win_x + win_w / 2
            center_y = win_y + win_h / 2
            
            # 获取全局鼠标位置
            mouse_x, mouse_y = get_global_mouse_pos()
            
            # 计算偏移量（y轴反转）
            sensitivity = 1.5
            offset_x = ((mouse_x - center_x) / (win_w / 2)) * sensitivity
            offset_y = -((mouse_y - center_y) / (win_h / 2)) * sensitivity
            
            # 限制在 -1.0 ~ 1.0 范围内
            offset_x = max(-1.0, min(1.0, offset_x))
            offset_y = max(-1.0, min(1.0, offset_y))
            
            return offset_x, offset_y
            
        except Exception as e:
            logger.debug(f"Eye tracking calc failed: {e}")
            return self.mouse_x, self.mouse_y
    
    def _get_mouse_follow_params(self) -> dict:
        """
        🚨 计算鼠标跟随参数（头部+身体+眼神）
        返回参数字典用于设置 Live2D 模型
        """
        if not self._eye_tracking_enabled:
            return {}
        
        # 🚨 如果动作正在播放，暂停鼠标跟随参数设置
        if self._motion_playing:
            return {}
        
        try:
            # 获取基础眼动值 (-1.0 ~ 1.0)
            eye_x, eye_y = self._get_eye_tracking_values()
            
            # 配置参数（与 brain 保持一致）
            head_sensitivity = 0.8
            body_sensitivity = 0.6
            eye_sensitivity = 1.2
            head_max_angle = 30
            body_max_angle = 30
            eye_max_offset = 1.5
            
            # 死区处理
            dead_zone = 0.08
            if abs(eye_x) < dead_zone:
                eye_x = 0.0
            else:
                eye_x = (abs(eye_x) - dead_zone) / (1 - dead_zone) * (1 if eye_x > 0 else -1)
            if abs(eye_y) < dead_zone:
                eye_y = 0.0
            else:
                eye_y = (abs(eye_y) - dead_zone) / (1 - dead_zone) * (1 if eye_y > 0 else -1)
            
            params = {}
            
            # === 头部跟随 (更大角度) ===
            params["ParamAngleX"] = eye_x * head_max_angle * head_sensitivity
            params["ParamAngleY"] = eye_y * head_max_angle * head_sensitivity
            params["ParamAngleZ"] = eye_x * head_max_angle * 0.3 * head_sensitivity
            
            # === 身体跟随 (延迟于头部，增加层次感) ===
            params["ParamBodyAngleX"] = eye_x * body_max_angle * body_sensitivity
            params["ParamBodyAngleY"] = eye_y * body_max_angle * 0.5 * body_sensitivity
            params["ParamBodyAngleZ"] = eye_x * body_max_angle * 0.4 * body_sensitivity
            
            # === 眼神跟随 (最灵活) ===
            params["ParamEyeBallX"] = eye_x * eye_max_offset * eye_sensitivity
            params["ParamEyeBallY"] = eye_y * eye_max_offset * eye_sensitivity
            
            return params
            
        except Exception as e:
            logger.debug(f"Mouse follow calc failed: {e}")
            return {}

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

            # 🚨 获取鼠标跟随参数（头部+身体+眼神）
            follow_params = self._get_mouse_follow_params()
            
            # 在 Update 之前设置参数
            if follow_params:
                try:
                    self.model.SetParameterValue("ParamEyeBallX", follow_params.get("ParamEyeBallX", 0))
                    self.model.SetParameterValue("ParamEyeBallY", follow_params.get("ParamEyeBallY", 0))
                    self.model.SetParameterValue("ParamEyeBallX2", follow_params.get("ParamEyeBallX", 0))
                    self.model.SetParameterValue("ParamEyeBallY2", follow_params.get("ParamEyeBallY", 0))
                except Exception as e:
                    logger.debug(f"Pre-update eye params failed: {e}")

            self.model.Update()  # Live2D 引擎会在这一步吸收你的嘴型参数并计算物理效果
            
            # Update 之后再设置一次（覆盖物理重置）
            if follow_params:
                try:
                    # 眼神
                    self.model.SetParameterValue("ParamEyeBallX", follow_params.get("ParamEyeBallX", 0))
                    self.model.SetParameterValue("ParamEyeBallY", follow_params.get("ParamEyeBallY", 0))
                    self.model.SetParameterValue("ParamEyeBallX2", follow_params.get("ParamEyeBallX", 0))
                    self.model.SetParameterValue("ParamEyeBallY2", follow_params.get("ParamEyeBallY", 0))
                    # 头部跟随
                    self.model.SetParameterValue("ParamAngleX", follow_params.get("ParamAngleX", 0))
                    self.model.SetParameterValue("ParamAngleY", follow_params.get("ParamAngleY", 0))
                    self.model.SetParameterValue("ParamAngleZ", follow_params.get("ParamAngleZ", 0))
                    # 身体跟随
                    self.model.SetParameterValue("ParamBodyAngleX", follow_params.get("ParamBodyAngleX", 0))
                    self.model.SetParameterValue("ParamBodyAngleY", follow_params.get("ParamBodyAngleY", 0))
                    self.model.SetParameterValue("ParamBodyAngleZ", follow_params.get("ParamBodyAngleZ", 0))
                except Exception as e:
                    logger.debug(f"Post-update mouse follow params failed: {e}")
            
            # 保存当前值供其他方法使用
            if follow_params:
                self.mouse_x = follow_params.get("ParamEyeBallX", 0)
                self.mouse_y = follow_params.get("ParamEyeBallY", 0)
          
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
    
    def find_expression(self, name: str) -> Optional[str]:
        """
        查找表情名称，支持映射转换
        返回实际可用的表情名称，如果找不到则返回 None
        """
        if not name:
            return None
        
        name_lower = name.lower()
        
        # 1. 首先检查是否在映射表中
        if name_lower in self._expression_mapping:
            mapped = self._expression_mapping[name_lower]
            logger.debug(f"Expression '{name}' mapped to '{mapped}'")
            return mapped
        
        # 2. 检查是否是已知的参数化表情
        if name_lower in self.EXPRESSION_PARAM_MAP:
            return name_lower
        
        # 3. 检查是否是 normal/reset
        if name_lower in ["normal", "reset"]:
            return "normal"
        
        logger.warning(f"Expression '{name}' not found in any mapping")
        return None
    
    def get_available_expressions(self) -> List[str]:
        """获取所有可用表情列表"""
        # 返回参数化表情的键列表
        return list(self.EXPRESSION_PARAM_MAP.keys()) + ["normal"]
    
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
        """🚨 【触觉反馈】触发动画/动作 - 仅使用原生 StartMotion (MotionPlayer 已禁用)"""
        if not self.model or not HAS_LIVE2D:
            logger.warning("Cannot trigger motion: model not loaded")
            return False
        
        logger.info(f"🎬 Attempting to trigger motion: {group}[{index}]")
        
        # 只使用原生 StartMotion (MotionPlayer 暂时禁用，因为不够流畅)
        try:
            priority = live2d.MotionPriority.FORCE
            result = self.model.StartMotion(group, index, priority)
            # 🚨 StartMotion 返回值不可靠，可能返回 None/False 但动作实际已播放
            # 只要没有异常抛出，就视为成功
            logger.info(f"✅ Motion triggered: {group}[{index}] (return={result})")
            self._motion_playing = True
            self._motion_playing_timer.start(100)
            return True
        except Exception as e:
            logger.debug(f"StartMotion failed: {e}")
        
        # === MotionPlayer 备选方案 (暂时禁用，因为不够流畅) ===
        # if self._motion_player and group in self._motion_files:
        #     try:
        #         motion_file = self._motion_files[group]
        #         logger.info(f"🎬 Falling back to MotionPlayer: {group}")
        #         success = self._motion_player.play(motion_file, loop=False)
        #         if success:
        #             logger.info(f"✅ Motion started via MotionPlayer: {group}")
        #             self._motion_playing = True
        #             return True
        #     except Exception as e:
        #         logger.error(f"❌ MotionPlayer error: {e}")
        
        logger.warning(f"⚠️ Failed to trigger motion: {group}")
        return False
    
    def _check_motion_finished(self):
        """🚨 检查动作是否播放完成"""
        if not self.model or not HAS_LIVE2D:
            self._motion_playing = False
            self._motion_playing_timer.stop()
            return
        
        try:
            # 检查是否有动作正在播放
            if self.model.IsMotionFinished():
                self._motion_playing = False
                self._motion_playing_timer.stop()
                logger.debug("🎬 Motion finished, resuming mouse follow")
        except Exception as e:
            logger.debug(f"Check motion status failed: {e}")
            # 出错时默认恢复鼠标跟随
            self._motion_playing = False
            self._motion_playing_timer.stop()
    
    def _detect_touch_part(self, x: int, y: int) -> str:
        """
        🚨 【触觉反馈】根据触摸坐标检测触摸部位
        窗口大小: 400x600
        返回: 头顶, 脸颊, 左耳, 右耳, 身体, 左手, 右手, 尾巴
        """
        width = self.width()
        height = self.height()
        
        # 归一化坐标 (0-1)
        nx = x / width
        ny = y / height
        
        # 区域定义 (基于雪莉模型的布局)
        if ny < 0.25:  # 上半部分 (0-25%)
            if 0.35 < nx < 0.65:
                return "头顶"
            elif nx <= 0.35:
                return "左耳"
            else:
                return "右耳"
        elif ny < 0.45:  # 上中部分 (25-45%)
            if 0.25 < nx < 0.75:
                return "脸颊"
            elif nx <= 0.25:
                return "左耳"
            else:
                return "右耳"
        elif ny < 0.70:  # 中间部分 (45-70%) - 身体区域
            if 0.2 < nx < 0.8:
                return "身体"
            elif nx <= 0.2:
                return "左手"
            else:
                return "右手"
        elif ny < 0.85:  # 下中部分 (70-85%)
            if nx <= 0.3:
                return "左手"
            elif nx >= 0.7:
                return "右手"
            else:
                return "尾巴"
        else:  # 底部 (85-100%)
            return "尾巴"
    
    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton and self.model:
            # 获取触摸位置
            pos = event.position()
            x = int(pos.x())
            y = int(pos.y())
            
            # 检测触摸部位
            part = self._detect_touch_part(x, y)
            logger.info(f"👆 Touch detected at ({x}, {y}) -> {part}")
            
            # 🚨 【触觉反馈】发射触摸事件信号
            self.touched.emit("tap", part)
            
            # 触发摸脸效果（保持原有效果）
            self.set_parameter("Key39", 1.0)
            self._touch_timer.start(1500)
        super().mousePressEvent(event)
    
    def _on_touch_end(self):
        if self.model:
            self.set_parameter("Key39", 0.0)
            logger.info("👋 Touch interaction ended")
    
    def set_eye_tracking_enabled(self, enabled: bool):
        """Enable or disable eye tracking"""
        self._eye_tracking_enabled = enabled
        if not enabled:
            self.mouse_x = 0.0
            self.mouse_y = 0.0
        logger.info(f"👁️ Eye tracking {'enabled' if enabled else 'disabled'}")

    def reset_pose(self, duration_ms: float = 3000):
        """
        🚨 强制回正头部和身体（用于TTS说话时）
        暂时禁用鼠标跟随，重置所有姿势参数
        duration_ms: 回正保持时间（毫秒），默认3秒
        """
        if not self.model or not HAS_LIVE2D:
            return
        
        logger.info(f"🎯 Live2DView: 强制回正姿势（持续 {duration_ms}ms）")
        
        # 1. 禁用鼠标跟随
        self._eye_tracking_enabled = False
        
        # 2. 重置所有姿势参数为0
        reset_params = {
            "ParamAngleX": 0.0, "ParamAngleY": 0.0, "ParamAngleZ": 0.0,
            "ParamBodyAngleX": 0.0, "ParamBodyAngleY": 0.0, "ParamBodyAngleZ": 0.0,
            "ParamEyeBallX": 0.0, "ParamEyeBallY": 0.0,
            "ParamEyeBallX2": 0.0, "ParamEyeBallY2": 0.0
        }
        
        for param_id, value in reset_params.items():
            try:
                self.model.SetParameterValue(param_id, value)
            except Exception as e:
                logger.debug(f"Failed to reset {param_id}: {e}")
        
        # 3. 重置内部状态
        self.mouse_x = 0.0
        self.mouse_y = 0.0
        
        # 4. 强制刷新
        self.update()
        
        # 5. 使用 QTimer 延迟恢复鼠标跟随
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(int(duration_ms), self._restore_mouse_follow)
    
    def _restore_mouse_follow(self):
        """恢复鼠标跟随"""
        logger.info("🐭 Live2DView: 恢复鼠标跟随")
        self._eye_tracking_enabled = True
    
    def _update_eye_tracking(self):
        """Update eye tracking based on global mouse position (Windows API)"""
        if not self._eye_tracking_enabled or not self.model:
            return
        
        try:
            # Get window geometry
            from PyQt6.QtCore import QPoint
            window_pos = self.mapToGlobal(QPoint(0, 0))
            win_x = window_pos.x()
            win_y = window_pos.y()
            win_w = self.width()
            win_h = self.height()
            
            # Calculate window center
            center_x = win_x + win_w / 2
            center_y = win_y + win_h / 2
            
            # Get global mouse position using Windows API
            mouse_x, mouse_y = get_global_mouse_pos()
            
            # Calculate offset from center (normalized to -1.0 ~ 1.0)
            # Note: y轴需要反转，因为屏幕坐标y向下，而Live2D坐标y向上
            sensitivity = 1.5
            
            self.mouse_x = ((mouse_x - center_x) / (win_w / 2)) * sensitivity
            self.mouse_y = -((mouse_y - center_y) / (win_h / 2)) * sensitivity  # 反转y轴
            
            # Clamp to valid range
            self.mouse_x = max(-1.0, min(1.0, self.mouse_x))
            self.mouse_y = max(-1.0, min(1.0, self.mouse_y))
            
            # Debug: 每5秒输出一次坐标
            import time
            if not hasattr(self, '_last_debug_time'):
                self._last_debug_time = 0
            now = time.time()
            if now - self._last_debug_time > 5:
                logger.info(f"👁️ Eye tracking: mouse=({mouse_x},{mouse_y}), window=({win_x},{win_y}), offset=({self.mouse_x:.2f},{self.mouse_y:.2f})")
                self._last_debug_time = now
            
        except Exception as e:
            logger.debug(f"Eye tracking update failed: {e}")
    
    def cleanup(self):
        self.update_timer.stop()
        self._lip_sync_timer.stop()
        self._eye_tracking_timer.stop()
        if HAS_LIVE2D and self._live2d_initialized:
            try:
                live2d.dispose()
                self._live2d_initialized = False
            except:
                pass
        
        # 🚨 清理临时 model.json 文件
        if self._temp_model_json and self._temp_model_json.exists():
            try:
                self._temp_model_json.unlink()
                logger.debug(f"🗑️ 清理临时文件: {self._temp_model_json}")
            except:
                pass
