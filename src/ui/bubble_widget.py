#!/usr/bin/env python3
"""
Bubble Widget - Floating message bubble for Sherry
"""

from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout, QGraphicsDropShadowEffect
from PyQt6.QtCore import Qt, QTimer, QPoint, QSize
from PyQt6.QtGui import QColor, QFont, QPainterPath, QRegion


class BubbleWidget(QWidget):
    """Floating message bubble"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self._setup_ui()
        self._setup_style()
        
        # Timer for auto-hide
        self.hide_timer = QTimer(self)
        self.hide_timer.timeout.connect(self.hide)
    
    def _setup_ui(self):
        """Setup UI components"""
        
        # Frameless, transparent window
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # Layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 15, 20, 25)
        layout.setSpacing(0)
        
        # Message label
        self.message_label = QLabel(self)
        self.message_label.setWordWrap(True)
        self.message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.message_label)
        
        # Default size
        self.setMinimumWidth(200)
        self.setMaximumWidth(350)
    
    def _setup_style(self):
        """Setup visual style"""
        
        # Sherry color scheme - purple theme
        self.setStyleSheet("""
            QWidget {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 rgba(155, 126, 222, 240),
                    stop: 1 rgba(180, 140, 240, 240)
                );
                border-radius: 20px;
                border: 2px solid rgba(255, 255, 255, 200);
            }
            QLabel {
                background: transparent;
                border: none;
                color: white;
                font-size: 14px;
                font-weight: 500;
                padding: 5px;
            }
        """)
        
        # Drop shadow
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(100, 50, 150, 150))
        shadow.setOffset(0, 4)
        self.setGraphicsEffect(shadow)
    
    def show_message(self, text: str, duration: int = 5000):
        """Show message bubble"""
        
        self.message_label.setText(text)
        self.adjustSize()
        
        # Position above the sprite window
        if self.parent():
            parent_rect = self.parent().geometry()
            x = parent_rect.center().x() - self.width() // 2
            y = parent_rect.top() - self.height() - 10
            self.move(x, y)
        
        self.show()
        self.raise_()
        
        # Auto-hide after duration
        if duration > 0:
            self.hide_timer.start(duration)
        else:
            self.hide_timer.stop()
    
    def paintEvent(self, event):
        """Custom paint for bubble tail"""
        super().paintEvent(event)
        
        # Could add bubble tail drawing here
        pass
