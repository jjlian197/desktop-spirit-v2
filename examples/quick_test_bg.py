#!/usr/bin/env python3
"""
快速测试背景切换
"""

import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer
from src.core.sprite_window import SherrySpriteWindow


def test():
    app = QApplication(sys.argv)
    window = SherrySpriteWindow()
    window.show()
    
    print("背景切换测试 - 2秒切换一次")
    print("=" * 50)
    
    colors = [
        ("#FF0000", "红色"),
        ("#00FF00", "绿色"),
        ("#0000FF", "蓝色"),
        ("#FFFF00", "黄色"),
        ("transparent", "透明"),
    ]
    
    step = [0]
    
    def next_color():
        if step[0] < len(colors):
            color, name = colors[step[0]]
            print(f"设置: {name} ({color})")
            window.set_background(color)
            step[0] += 1
            QTimer.singleShot(2000, next_color)
        else:
            print("测试完成")
            app.quit()
    
    QTimer.singleShot(500, next_color)
    app.exec()


if __name__ == "__main__":
    test()
