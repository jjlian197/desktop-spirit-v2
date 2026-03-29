#!/usr/bin/env python3
"""
Sherry Sprite Window - Transparent, Frameless, Always-on-Top
"""

import sys
import os
import platform
import subprocess
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
    from src.core.live2d_view import Live2DView, HAS_LIVE2D, get_project_dir
except ImportError:
    HAS_LIVE2D = False
    def get_project_dir():
        return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        
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
                # 💜 使用绝对路径加载模型（支持 .app 包）
                project_dir = get_project_dir()
                model_path = os.path.join(project_dir, "src", "assets", "models", "hanamaru")
                logger.info(f"📦 Loading model from: {model_path}")
                
                # 💜 强制创建 OpenGL 上下文
                self.live2d_view.show()
                self.live2d_view.update()
                
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
        
        # 💜 设置托盘图标
        icon_paths = [
            os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "sherry.icns"),
            os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "sherry.png"),
        ]
        for icon_path in icon_paths:
            if os.path.exists(icon_path):
                self.tray_icon.setIcon(QIcon(icon_path))
                break
        
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
            ("Happy", "star_eye"),
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

        tts_menu.addSeparator()

        # 🌐 Language selection submenu
        language_menu = tts_menu.addMenu("🌐 语言 (Language)")
        if HAS_TTS and self.tts_manager:
            languages = self.tts_manager.get_available_languages()
            current_lang = self.tts_manager.get_current_language()
            for lang_code, lang_name in languages.items():
                action = QAction(f"{lang_name} ({lang_code.upper()})", self)
                action.setCheckable(True)
                action.setChecked(current_lang == lang_code)
                action.triggered.connect(lambda checked, l=lang_code: self._switch_language(l))
                language_menu.addAction(action)
        else:
            no_lang_action = QAction("语言切换不可用", self)
            no_lang_action.setEnabled(False)
            language_menu.addAction(no_lang_action)

        tts_menu.addSeparator()

        # 🎙️ GPT-SoVITS 配置菜单
        if HAS_TTS and self.tts_manager and "gptsovits" in self.tts_manager.providers:
            gptsovits_menu = tts_menu.addMenu("🎙️ GPT-SoVITS 配置")
            
            # 显示当前参考音频文件名
            gptsovits_provider = self.tts_manager.providers.get("gptsovits")
            ref_path = ""
            if gptsovits_provider and hasattr(gptsovits_provider, 'config'):
                ref_path = gptsovits_provider.config.refer_wav_path or ""
            ref_filename = ref_path.split("/")[-1].split("\\")[-1] if ref_path else "未设置"
            
            # 参考音频配置
            ref_action = QAction(f"📁 参考音频: {ref_filename[:20]}...", self)
            ref_action.triggered.connect(self._configure_gptsovits_ref)
            gptsovits_menu.addAction(ref_action)
            
            # 参考文本配置
            prompt_text = ""
            if gptsovits_provider and hasattr(gptsovits_provider, 'config'):
                prompt_text = gptsovits_provider.config.prompt_text or ""
            prompt_display = prompt_text[:15] + "..." if prompt_text else "未设置"
            prompt_action = QAction(f"📝 参考文本: {prompt_display}", self)
            prompt_action.triggered.connect(self._configure_gptsovits_prompt)
            gptsovits_menu.addAction(prompt_action)
            
            # 语速配置子菜单
            speed_menu = gptsovits_menu.addMenu("⚡ 语速")
            current_speed = 1.0
            if gptsovits_provider and hasattr(gptsovits_provider, 'config'):
                current_speed = gptsovits_provider.config.speed
            
            for speed_label, speed_value in [
                ("0.8x 慢速", 0.8),
                ("1.0x 正常", 1.0),
                ("1.2x 稍快", 1.2),
                ("1.5x 快速", 1.5),
            ]:
                action = QAction(speed_label, self)
                action.setCheckable(True)
                action.setChecked(abs(current_speed - speed_value) < 0.01)
                action.triggered.connect(lambda checked, s=speed_value: self._configure_gptsovits_speed(s))
                speed_menu.addAction(action)
            
            gptsovits_menu.addSeparator()
            
            # 恢复默认配置
            reset_action = QAction("🔄 恢复默认 (Sakiko)", self)
            reset_action.triggered.connect(self._reset_gptsovits_config)
            gptsovits_menu.addAction(reset_action)
            
            tts_menu.addSeparator()

        # Test phrases
        test_phrases = [
            ("你好，世界！", "你好，世界！我是雪莉~"),
            ("测试语音", "这是一个语音测试，你能听到我说话吗？"),
            ("长句测试", "今天天气真不错，适合出去散步和喝咖啡呢！"),
            ("日文测试", "こんにちは、シェリーです~"),
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
        
        # 🖱️ 鼠标跟随开关
        mouse_follow_action = QAction("🖱️ 鼠标跟随 (Mouse Follow)", self)
        mouse_follow_action.setCheckable(True)
        mouse_follow_enabled = self._get_mouse_follow_state()
        mouse_follow_action.setChecked(mouse_follow_enabled)
        mouse_follow_action.triggered.connect(self._toggle_mouse_follow)
        menu.addAction(mouse_follow_action)
        
        menu.addSeparator()
        
        # 🏠 回家模式
        home_mode_action = QAction("🏠 启动回家模式", self)
        home_mode_action.triggered.connect(self._launch_home_mode)
        menu.addAction(home_mode_action)
        
        menu.addSeparator()
        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(QApplication.quit)
        menu.addAction(quit_action)

        menu.exec(pos)

    def _toggle_watermark(self):
        self._watermark_enabled = not self._watermark_enabled
        val = -1.0 if self._watermark_enabled else 0.0
        self.set_parameter("Open_EyeMask4", val)
    
    def _launch_home_mode(self):
        """🏠 启动回家模式 - 通过 openclaw 发送消息"""
        try:
            # 执行终端命令
            cmd = ["openclaw", "agent", "--agent", "main", "--message", "我回来了"]
            subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True  # 避免子进程随父进程退出
            )
            logger.info("🏠 回家模式已启动: openclaw agent --agent main --message '我回来了'")
            # 显示反馈气泡
            self.show_message("已启动回家模式~", 2000)
        except FileNotFoundError:
            logger.error("❌ 未找到 openclaw 命令，请确保已安装并添加到 PATH")
            self.show_message("错误：未找到 openclaw 命令", 3000)
        except Exception as e:
            logger.error(f"❌ 启动回家模式失败: {e}")
            self.show_message(f"启动失败: {e}", 3000)
    
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

    def _switch_language(self, lang_code: str):
        """🌐 切换 TTS 语言 (zh/jp)"""
        if not HAS_TTS or not self.tts_manager:
            self.show_message("❌ TTS 不可用")
            return
        
        success = self.tts_manager.set_language(lang_code)
        if success:
            lang_name = "中文" if lang_code == "zh" else "日语"
            self.show_message(f"🌐 已切换到: {lang_name}")
            logger.info(f"Language switched to: {lang_code} ({lang_name})")
        else:
            self.show_message(f"❌ 语言切换失败: {lang_code}")

    def _configure_gptsovits_ref(self):
        """🎙️ 配置 GPT-SoVITS 参考音频路径"""
        if not HAS_TTS or not self.tts_manager:
            self.show_message("❌ TTS 不可用")
            return
        
        gptsovits = self.tts_manager.providers.get("gptsovits")
        if not gptsovits:
            self.show_message("❌ GPT-SoVITS 不可用")
            return
        
        # 获取当前路径
        current_path = ""
        if hasattr(gptsovits, 'config'):
            current_path = gptsovits.config.refer_wav_path or ""
        
        # 显示输入对话框
        from PyQt6.QtWidgets import QInputDialog, QMessageBox
        
        text, ok = QInputDialog.getText(
            self,
            "配置参考音频",
            "请输入参考音频的完整路径:\n(服务器上的路径，如 D:/ref.wav)",
            text=current_path
        )
        
        if ok and text:
            if hasattr(gptsovits, 'config'):
                gptsovits.config.refer_wav_path = text
                filename = text.split("/")[-1].split("\\")[-1]
                self.show_message(f"🎙️ 参考音频已更新:\n{filename[:30]}")
                logger.info(f"GPT-SoVITS 参考音频更新: {text}")

    def _configure_gptsovits_prompt(self):
        """🎙️ 配置 GPT-SoVITS 参考文本"""
        if not HAS_TTS or not self.tts_manager:
            self.show_message("❌ TTS 不可用")
            return
        
        gptsovits = self.tts_manager.providers.get("gptsovits")
        if not gptsovits:
            self.show_message("❌ GPT-SoVITS 不可用")
            return
        
        # 获取当前文本
        current_text = ""
        if hasattr(gptsovits, 'config'):
            current_text = gptsovits.config.prompt_text or ""
        
        from PyQt6.QtWidgets import QInputDialog
        
        text, ok = QInputDialog.getText(
            self,
            "配置参考文本",
            "请输入参考音频对应的文本内容:",
            text=current_text
        )
        
        if ok and text:
            if hasattr(gptsovits, 'config'):
                gptsovits.config.prompt_text = text
                display = text[:20] + "..." if len(text) > 20 else text
                self.show_message(f"📝 参考文本已更新:\n{display}")
                logger.info(f"GPT-SoVITS 参考文本更新: {text[:50]}...")

    def _configure_gptsovits_speed(self, speed: float):
        """🎙️ 配置 GPT-SoVITS 语速"""
        if not HAS_TTS or not self.tts_manager:
            return
        
        gptsovits = self.tts_manager.providers.get("gptsovits")
        if gptsovits and hasattr(gptsovits, 'config'):
            gptsovits.config.speed = speed
            self.show_message(f"⚡ 语速已设置为: {speed}x")
            logger.info(f"GPT-SoVITS 语速更新: {speed}x")

    def _reset_gptsovits_config(self):
        """🎙️ 恢复 GPT-SoVITS 默认配置 (Sakiko)"""
        if not HAS_TTS or not self.tts_manager:
            self.show_message("❌ TTS 不可用")
            return
        
        gptsovits = self.tts_manager.providers.get("gptsovits")
        if not gptsovits:
            self.show_message("❌ GPT-SoVITS 不可用")
            return
        
        if hasattr(gptsovits, 'config'):
            # 恢复 Sakiko 默认配置
            gptsovits.config.refer_wav_path = "D:/Workspace/1761703720454-qatfwm-sakiko1-e15/参考/なんだか申し訳ありませんわそれにしても可愛らしいお部屋ですわね.wav"
            gptsovits.config.prompt_text = "なんだか申し訳ありませんわそれにしても可愛らしいお部屋ですわね"
            gptsovits.config.prompt_language = "ja"
            gptsovits.config.speed = 1.0
            
            self.show_message("🔄 GPT-SoVITS 已恢复默认\n🎀 Sakiko 声音配置")
            logger.info("GPT-SoVITS 配置已恢复为默认值 (Sakiko)")

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

    def _get_mouse_follow_state(self) -> bool:
        """Get current mouse follow state from backend"""
        try:
            import urllib.request
            import urllib.error
            import json
            
            req = urllib.request.Request(
                "http://127.0.0.1:8766/health",
                method='GET'
            )
            
            with urllib.request.urlopen(req, timeout=1) as response:
                if response.status == 200:
                    result = json.loads(response.read().decode('utf-8'))
                    return result.get('mouse_follow_enabled', True)
        except Exception as e:
            logger.debug(f"Failed to get mouse follow state: {e}")
        
        # Default to enabled if backend not available
        return True

    def _toggle_mouse_follow(self, checked: bool):
        """Toggle mouse follow switch via HTTP API"""
        from PyQt6.QtCore import QTimer
        
        def send_mouse_follow_request():
            try:
                import urllib.request
                import urllib.error
                import json
                
                action = "on" if checked else "off"
                data = json.dumps({"action": action}).encode('utf-8')
                
                req = urllib.request.Request(
                    "http://127.0.0.1:8766/api/mouse_follow",
                    data=data,
                    headers={'Content-Type': 'application/json'},
                    method='POST'
                )
                
                with urllib.request.urlopen(req, timeout=2) as response:
                    if response.status == 200:
                        self.show_message(f"🖱️ 鼠标跟随: {'开启' if checked else '关闭'}")
                    else:
                        self.show_message(f"⚠️ 鼠标跟随状态已切换 (HTTP {response.status})")
                        
            except urllib.error.URLError as e:
                logger.error(f"Mouse follow HTTP request failed: {e}")
                self.show_message(f"⚠️ 鼠标跟随状态已切换 (后端未响应)")
            except Exception as e:
                logger.error(f"Mouse follow toggle error: {e}")
                self.show_message(f"⚠️ 鼠标跟随状态已切换")
        
        # Use QTimer to avoid blocking UI
        QTimer.singleShot(0, send_mouse_follow_request)
