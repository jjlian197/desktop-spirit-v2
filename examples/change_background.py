#!/usr/bin/env python3
"""
背景切换示例
演示如何通过 HTTP API 更换雪莉的背景
"""

import requests
import json
import time

HTTP_API = "http://127.0.0.1:8766"


def set_background(bg_type, path=None):
    """设置背景"""
    data = {"type": bg_type}
    if path:
        data["path"] = path
    
    response = requests.post(f"{HTTP_API}/api/background", json=data)
    print(f"Set background to {bg_type}: {response.json()}")


def main():
    """演示各种背景效果"""
    print("雪莉背景切换演示")
    print("=" * 50)
    
    # 1. 纯色背景 - 粉色
    print("\n1. 设置粉色背景...")
    set_background("#FF69B4")
    time.sleep(2)
    
    # 2. 纯色背景 - 浅蓝色
    print("\n2. 设置浅蓝色背景...")
    set_background("#87CEEB")
    time.sleep(2)
    
    # 3. 渐变背景
    print("\n3. 设置渐变背景...")
    set_background("gradient:linear:#FF5733:#33FF57")
    time.sleep(2)
    
    # 4. 预设颜色 - 深色
    print("\n4. 设置深色背景...")
    set_background("dark")
    time.sleep(2)
    
    # 5. 透明背景（恢复默认）
    print("\n5. 恢复透明背景...")
    set_background("transparent")
    
    print("\n演示完成！")


def cycle_backgrounds():
    """循环切换各种背景"""
    colors = [
        "#FF69B4",  # 粉色
        "#87CEEB",  # 浅蓝
        "#FFD700",  # 金色
        "#98FB98",  # 浅绿
        "#DDA0DD",  # 梅花色
        "#F0E68C",  # 卡其色
        "transparent",  # 透明
    ]
    
    print("循环切换背景（按 Ctrl+C 停止）...")
    try:
        while True:
            for color in colors:
                set_background(color)
                time.sleep(1.5)
    except KeyboardInterrupt:
        print("\n停止循环，恢复透明背景...")
        set_background("transparent")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "cycle":
        cycle_backgrounds()
    else:
        main()
