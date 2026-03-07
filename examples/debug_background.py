#!/usr/bin/env python3
"""
调试背景切换问题
"""

import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer
from src.core.sprite_window import SherrySpriteWindow


def test_background():
    app = QApplication(sys.argv)
    window = SherrySpriteWindow()
    window.show()
    
    print("=" * 60)
    print("背景调试测试")
    print("=" * 60)
    
    # 检查 central_widget
    print(f"\n1. central_widget: {window.central_widget}")
    print(f"   objectName: {window.central_widget.objectName()}")
    print(f"   styleSheet (before): {window.central_widget.styleSheet()[:100] if window.central_widget.styleSheet() else 'empty'}")
    
    # 测试设置红色背景
    print("\n2. 设置红色背景...")
    window.set_background("#FF0000")
    
    print(f"   styleSheet (after): {window.central_widget.styleSheet()[:100] if window.central_widget.styleSheet() else 'empty'}")
    print(f"   autoFillBackground: {window.central_widget.autoFillBackground()}")
    
    # 检查 palette
    from PyQt6.QtGui import QPalette
    palette = window.central_widget.palette()
    color = palette.color(QPalette.ColorRole.Window)
    print(f"   palette color: {color.name() if color else 'None'}")
    
    # 检查透明属性
    print(f"\n3. WA_TranslucentBackground: {window.testAttribute(window.WidgetAttribute.WA_TranslucentBackground)}")
    
    # 3秒后关闭
    QTimer.singleShot(3000, app.quit)
    app.exec()
    
    print("\n测试完成")


if __name__ == "__main__":
    test_background()
