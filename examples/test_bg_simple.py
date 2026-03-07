#!/usr/bin/env python3
"""
简单测试背景切换
直接通过 HTTP API 测试
"""

import requests
import time

BASE_URL = "http://127.0.0.1:8766"


def test_bg(color, name):
    """测试设置背景"""
    print(f"\n设置背景: {name} ({color})")
    try:
        resp = requests.post(f"{BASE_URL}/api/background", 
                           json={"type": color}, 
                           timeout=5)
        print(f"  响应: {resp.json()}")
        time.sleep(1)
    except Exception as e:
        print(f"  错误: {e}")


def main():
    print("背景切换测试")
    print("=" * 50)
    
    # 测试各种背景
    test_bg("#FF0000", "红色")
    test_bg("#00FF00", "绿色")
    test_bg("#0000FF", "蓝色")
    test_bg("transparent", "透明")
    
    print("\n测试完成")


if __name__ == "__main__":
    main()
