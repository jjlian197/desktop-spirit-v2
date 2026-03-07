#!/usr/bin/env python3
"""
测试背景切换功能
直接调用 set_background 方法进行测试
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer
from src.core.sprite_window import SherrySpriteWindow
import time


def test_backgrounds():
    """测试各种背景"""
    app = QApplication(sys.argv)
    window = SherrySpriteWindow()
    window.show()
    
    tests = [
        ("#FF5733", "红色"),
        ("#33FF57", "绿色"),
        ("#3357FF", "蓝色"),
        ("gradient:linear:#FF5733:#33FF57", "渐变"),
        ("transparent", "透明"),
    ]
    
    current = [0]
    
    def next_test():
        if current[0] < len(tests):
            bg_type, name = tests[current[0]]
            print(f"设置背景: {name} ({bg_type})")
            window.set_background(bg_type)
            current[0] += 1
            QTimer.singleShot(2000, next_test)
        else:
            print("测试完成")
            window.close()
            app.quit()
    
    QTimer.singleShot(1000, next_test)
    app.exec()


if __name__ == "__main__":
    test_backgrounds()
