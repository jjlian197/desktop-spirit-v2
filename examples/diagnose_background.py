#!/usr/bin/env python3
"""
诊断背景问题
检查所有与背景/透明相关的属性
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt, QTimer
from src.core.sprite_window import SherrySpriteWindow


def diagnose():
    app = QApplication(sys.argv)
    window = SherrySpriteWindow()
    window.show()
    
    print("=" * 70)
    print("背景问题诊断")
    print("=" * 70)
    
    # 1. 检查窗口初始化状态
    print("\n【1. 窗口初始化状态】")
    print(f"   WA_TranslucentBackground: {window.testAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)}")
    print(f"   窗口样式表: {window.styleSheet()}")
    
    # 2. 检查 central_widget
    print("\n【2. Central Widget】")
    cw = window.central_widget
    print(f"   objectName: {cw.objectName()}")
    print(f"   styleSheet: {cw.styleSheet()}")
    print(f"   autoFillBackground: {cw.autoFillBackground()}")
    print(f"   WA_TranslucentBackground: {cw.testAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)}")
    
    # 3. 检查 Live2DView
    print("\n【3. Live2DView】")
    if window.live2d_view:
        lv = window.live2d_view
        print(f"   存在: True")
        print(f"   styleSheet: {lv.styleSheet()}")
        print(f"   autoFillBackground: {lv.autoFillBackground()}")
        print(f"   WA_TranslucentBackground: {lv.testAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)}")
        print(f"   WA_OpaquePaintEvent: {lv.testAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent)}")
    else:
        print(f"   存在: False")
    
    # 4. 检查 Palette
    print("\n【4. 窗口 Palette】")
    from PyQt6.QtGui import QPalette
    palette = window.palette()
    window_color = palette.color(QPalette.ColorRole.Window)
    base_color = palette.color(QPalette.ColorRole.Base)
    print(f"   Window color: {window_color.name() if window_color else 'None'}")
    print(f"   Base color: {base_color.name() if base_color else 'None'}")
    
    # 5. 尝试设置红色背景并检查
    print("\n【5. 设置红色背景后】")
    window.set_background("#FF0000")
    
    QTimer.singleShot(100, lambda: check_after_set(window))
    
    # 6秒后退出
    QTimer.singleShot(6000, app.quit)
    app.exec()


def check_after_set(window):
    print(f"   WA_TranslucentBackground: {window.testAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)}")
    print(f"   窗口样式表: {window.styleSheet()}")
    print(f"   central_widget 样式表: {window.central_widget.styleSheet()}")
    
    from PyQt6.QtGui import QPalette
    palette = window.palette()
    window_color = palette.color(QPalette.ColorRole.Window)
    print(f"   窗口 Palette Window color: {window_color.name() if window_color else 'None'}")
    
    # 检查 central_widget 实际背景
    cw_palette = window.central_widget.palette()
    cw_color = cw_palette.color(QPalette.ColorRole.Window)
    print(f"   central_widget Palette Window color: {cw_color.name() if cw_color else 'None'}")
    
    print("\n诊断完成，窗口将在3秒后关闭...")


if __name__ == "__main__":
    diagnose()
