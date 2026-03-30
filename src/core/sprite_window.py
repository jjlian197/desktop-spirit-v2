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

# Import STT Manager
try:
    from src.core.stt_manager import STTManager, create_stt_provider
    HAS_STT = True
except ImportError:
    HAS_STT = False
    logger.warning("STT 模块不可用")

# Import Agent Bridge toggle
try:
    from src.brain.agent_bridge import set_agent_bridge_enabled, is_agent_bridge_enabled
    HAS_AGENT_BRIDGE = True
except ImportError:
    HAS_AGENT_BRIDGE = False
    logger.warning("Agent Bridge 模块不可用")

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

        # Initialize STT manager
        self.stt_manager = None
        self._stt_listening = False
        if HAS_STT:
            try:
                self.stt_manager = create_stt_provider(language="zh")
                self.stt_manager.on_transcript = self._on_stt_transcript
                self.stt_manager.on_error = self._on_stt_error
                logger.info("✅ SpriteWindow: STT manager initialized")
            except Exception as e:
                logger.error(f"Failed to initialize STT manager: {e}")

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

        # 🎵 GPT-SoVITS Proxy 音色选择（多音色）
        if HAS_TTS and self.tts_manager and "gptsovits_proxy" in self.tts_manager.providers:
            proxy_menu = tts_menu.addMenu("🎵 GPT-SoVITS 音色")

            # 中文音色子菜单
            zh_voices = ["丁真", "七海", "东雪莲", "乃琳", "冰糖", "卡提希娅_zh", "向晚", "嘉然", "塔菲", "奶绿", "孙笑川", "守岸人_zh", "尼奈", "山泥若", "张顺飞", "恬豆", "扇宝", "扇宝（卖卖）", "文静", "星瞳", "李老八", "椿_zh", "炫神", "珂莱塔_zh", "珈乐", "电棍", "米诺", "菲比_zh", "蔡徐坤", "贝拉", "长离_zh", "阿梓", "陈泽"]
            zh_menu = proxy_menu.addMenu("🇨🇳 中文音色")
            for voice_name in zh_voices:
                action = QAction(voice_name, self)
                proxy_provider = self.tts_manager.providers.get("gptsovits_proxy")
                if proxy_provider:
                    action.setCheckable(True)
                    action.setChecked(proxy_provider.voice_id == voice_name)
                action.triggered.connect(lambda checked, v=voice_name: self._select_gptsovits_proxy_voice(v))
                zh_menu.addAction(action)

            # 日文音色子菜单
            ja_voices = ["sakiko1", "坎特蕾拉_ja", "守岸人_ja", "椿_ja", "珂莱塔_ja", "男漂泊者_ja", "芙宁娜_ja", "菲比_ja", "长离_ja", "阿布_ja"]
            ja_menu = proxy_menu.addMenu("🇯🇵 日文音色")
            for voice_name in ja_voices:
                action = QAction(voice_name, self)
                proxy_provider = self.tts_manager.providers.get("gptsovits_proxy")
                if proxy_provider:
                    action.setCheckable(True)
                    action.setChecked(proxy_provider.voice_id == voice_name)
                action.triggered.connect(lambda checked, v=voice_name: self._select_gptsovits_proxy_voice(v))
                ja_menu.addAction(action)

            # 英文音色子菜单
            en_menu = proxy_menu.addMenu("🇺🇸 英文音色")
            action = QAction("科比", self)
            proxy_provider = self.tts_manager.providers.get("gptsovits_proxy")
            if proxy_provider:
                action.setCheckable(True)
                action.setChecked(proxy_provider.voice_id == "科比")
            action.triggered.connect(lambda checked, v="科比": self._select_gptsovits_proxy_voice(v))
            en_menu.addAction(action)

            proxy_menu.addSeparator()

            # 切换到 GPT-SoVITS Proxy
            switch_action = QAction("🔄 切换到 GPT-SoVITS Proxy", self)
            switch_action.triggered.connect(lambda: self._switch_tts_provider("gptsovits_proxy"))
            proxy_menu.addAction(switch_action)

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

        # 🎤 语音识别 (STT) 菜单
        stt_menu = menu.addMenu("🎤 语音识别 (STT)")

        if HAS_STT and self.stt_manager:
            # 语音识别开关
            stt_toggle_action = QAction("🎙️ 开始语音对话", self)
            stt_toggle_action.setCheckable(True)
            stt_toggle_action.setChecked(self._stt_listening)
            stt_toggle_action.triggered.connect(self._toggle_stt_listening)
            stt_menu.addAction(stt_toggle_action)

            stt_menu.addSeparator()

            # 语言选择
            stt_lang_menu = stt_menu.addMenu("🌐 识别语言")
            stt_languages = self.stt_manager.get_available_languages()
            for lang_code, lang_name in stt_languages.items():
                action = QAction(f"{lang_name}", self)
                action.triggered.connect(lambda checked, l=lang_code: self._set_stt_language(l))
                stt_lang_menu.addAction(action)

            stt_menu.addSeparator()

            # 提示信息
            hint_action = QAction("💡 使用 macOS 原生语音识别", self)
            hint_action.setEnabled(False)
            stt_menu.addAction(hint_action)
        else:
            stt_unavailable = QAction("STT 不可用", self)
            stt_unavailable.setEnabled(False)
            stt_menu.addAction(stt_unavailable)

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

        # 🤖 Agent Bridge 开关
        if HAS_AGENT_BRIDGE:
            agent_bridge_action = QAction("🤖 Agent Bridge", self)
            agent_bridge_action.setCheckable(True)
            agent_bridge_action.setChecked(is_agent_bridge_enabled())
            agent_bridge_action.triggered.connect(self._toggle_agent_bridge)
            menu.addAction(agent_bridge_action)
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

    def _toggle_agent_bridge(self):
        """🤖 切换 Agent Bridge 开关状态"""
        if not HAS_AGENT_BRIDGE:
            return
        current = is_agent_bridge_enabled()
        set_agent_bridge_enabled(not current)
        status = "开启" if not current else "关闭"
        self.show_message(f"Agent Bridge 已{status}", 2000)

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

    def _select_gptsovits_proxy_voice(self, voice_name: str):
        """🎵 切换 GPT-SoVITS Proxy 音色"""
        if not HAS_TTS or not self.tts_manager:
            return

        proxy_provider = self.tts_manager.providers.get("gptsovits_proxy")
        if not proxy_provider:
            return

        # 切换到 proxy provider
        self.tts_manager.set_provider("gptsovits_proxy")

        # 设置音色
        proxy_provider.voice_id = voice_name

        self.show_message(f"🎵 音色已切换: {voice_name}")
        logger.info(f"GPT-SoVITS-Proxy 音色切换: {voice_name}")

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

    # === 🎤 STT 语音识别相关方法 ===

    def _toggle_stt_listening(self, checked: bool):
        """切换语音识别监听状态"""
        if not HAS_STT or not self.stt_manager:
            self.show_message("❌ STT 不可用", 2000)
            return

        from PyQt6.QtCore import QTimer

        def run_async(coro):
            """在 Qt 环境中安全运行异步函数"""
            import asyncio
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            # 在新线程中运行 asyncio
            import threading
            def _run():
                asyncio.run(coro)

            thread = threading.Thread(target=_run, daemon=True)
            thread.start()

        if checked:
            # 开始监听
            self.stt_manager.start_listening()
            self._stt_listening = True
            self.show_message("🎤 在听你说...", 2000)
            # 雪莉看向主人（假设主人在屏幕中央）
            self.set_expression("happy")
            logger.info("🎤 STT 监听已启动")
        else:
            # 停止监听
            self.stt_manager.stop_listening()
            self._stt_listening = False
            self.show_message("👋 语音对话已关闭", 2000)
            logger.info("🎤 STT 监听已停止")

    def _set_stt_language(self, language: str):
        """设置 STT 识别语言"""
        if not HAS_STT or not self.stt_manager:
            return

        if hasattr(self.stt_manager, 'set_language'):
            success = self.stt_manager.set_language(language)
            if success:
                lang_names = {
                    "zh": "中文",
                    "en": "英文",
                    "ja": "日文",
                    "ko": "韩文",
                }
                self.show_message(f"🌐 识别语言: {lang_names.get(language, language)}", 2000)

    def _on_stt_transcript(self, text: str, is_final: bool):
        """🎤 STT 识别到文字后的回调"""
        if not text or not is_final:
            return

        logger.info(f"🎤 STT 识别文字: {text}")

        # 检测唤醒词
        wake_words = ["雪莉", "Sherry", "sherry", "雪梨"]
        detected_name = None
        for name in wake_words:
            if name in text:
                detected_name = name
                break

        if not detected_name:
            return

        logger.info(f"🎤 检测到唤醒词: {detected_name}")

        # 提取唤醒词后面的内容
        idx = text.find(detected_name)
        user_text = text[idx + len(detected_name):].lstrip("，,、 ：:")

        if user_text:
            # 有具体内容 → 发送给 Agent
            self._send_voice_to_agent(user_text)
        else:
            # 只有唤醒词 → 简单确认
            self._voice_acknowledge()

    def _voice_acknowledge(self):
        """语音确认：告诉用户听到了"""
        def delayed_speak():
            import time
            time.sleep(0.3)
            self._do_tts_speak("主人我听到了！")

        import threading
        t = threading.Thread(target=delayed_speak, daemon=True)
        t.start()

    def _send_voice_to_agent(self, user_text: str):
        """发送语音内容给 Agent 并获取响应，通过 TTS 朗读"""
        from src.brain.agent_bridge import call_agent

        def agent_thread():
            try:
                logger.info(f"🎤 发送语音到 Agent: {user_text}")
                response = call_agent(message=user_text, timeout=60)

                if response:
                    logger.info(f"🎤 Agent 响应: {response[:50]}...")
                    self._do_tts_speak(response)
                else:
                    logger.warning("Agent 返回空响应")
                    self._do_tts_speak("抱歉，我没有收到回复")
            except Exception as e:
                logger.error(f"Agent 调用失败: {e}")
                self._do_tts_speak("抱歉，出错了")

        import threading
        t = threading.Thread(target=agent_thread, daemon=True)
        t.start()

    def _do_tts_speak(self, text: str):
        """执行 TTS 朗读（线程安全）"""
        try:
            if self.tts_manager and HAS_TTS:
                self.tts_manager.speak_sync(text)
            else:
                import subprocess
                subprocess.run(["say", text])
        except Exception as e:
            logger.error(f"TTS 朗读失败: {e}")
            try:
                import subprocess
                subprocess.run(["say", text])
            except Exception:
                pass

    def _send_to_brain(self, text: str):
        """发送文字给大脑处理"""
        import urllib.request
        import urllib.error
        import json

        try:
            data = json.dumps({
                "type": "chat",
                "data": {"message": text}
            }).encode('utf-8')

            req = urllib.request.Request(
                "http://127.0.0.1:8766/api/command",
                data=data,
                headers={'Content-Type': 'application/json'},
                method='POST'
            )

            with urllib.request.urlopen(req, timeout=5) as response:
                if response.status == 200:
                    logger.info(f"📤 已发送文字给大脑: {text}")
                else:
                    logger.warning(f"⚠️ 大脑响应异常: {response.status}")

        except urllib.error.URLError as e:
            logger.error(f"发送文字到大脑失败: {e}")
            # 如果大脑不响应，雪莉直接用本地回复
            self._local_chat_response(text)
        except Exception as e:
            logger.error(f"发送文字到大脑错误: {e}")
            self._local_chat_response(text)

    def _local_chat_response(self, text: str):
        """本地聊天回复（当大脑不可用时）"""
        # 简单的关键词回复
        text_lower = text.lower()

        responses = {
            "你好": "你好呀~主人！",
            "嗨": "嗨~主人！",
            "早上好": "早安~主人！",
            "晚安": "晚安~主人，好梦哦~",
            "可爱": "嘿嘿，雪莉被夸可爱了~",
            "喜欢你": "雪莉也最喜欢主人了！",
            "叫什么": "雪莉叫雪莉呀~主人的小宠物~",
            "几岁": "雪莉永远 18 岁哦~",
        }

        response = None
        for key, reply in responses.items():
            if key in text:
                response = reply
                break

        if not response:
            response = "嗯...雪莉听不太清楚呢~"

        self.set_expression("happy")
        self.show_message(f"💬 {response}", 3000)

        # 如果有 TTS，说出来
        if HAS_TTS and self.tts_manager:
            import threading
            def run_tts():
                try:
                    self.tts_manager.speak_sync(response)
                except Exception as e:
                    logger.error(f"TTS error: {e}")

            thread = threading.Thread(target=run_tts, daemon=True)
            thread.start()

    def _on_stt_error(self, error: str):
        """STT 错误回调"""
        logger.error(f"🎤 STT 错误: {error}")
        self.show_message(f"❌ 语音识别错误: {error}", 3000)
        self._stt_listening = False
