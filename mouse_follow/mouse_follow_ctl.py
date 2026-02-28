#!/usr/bin/env python3
"""
Sherry Desktop Sprite - 鼠标跟随控制器
"""

import subprocess
import sys
import os

def start_follow():
    """启动鼠标跟随"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    mouse_follow_sh = os.path.join(script_dir, "mouse_follow.sh")
    
    print("🐱 启动雪莉鼠标跟随系统...")
    subprocess.run(["bash", mouse_follow_sh])

def stop_follow():
    """停止鼠标跟随"""
    print("🛑 停止鼠标跟随...")
    subprocess.run(["pkill", "-f", "mouse_tracker.py"])
    print("✅ 已停止")

def reset_pose():
    """重置姿态"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    venv_python = os.path.join(script_dir, "venv/bin/python3")
    
    reset_script = """
import asyncio
import websockets
import json

async def reset():
    uri = 'ws://127.0.0.1:8765/sprite'
    async with websockets.connect(uri) as ws:
        params = ['ParamAngleX', 'ParamAngleY', 'ParamEyeBallX', 'ParamEyeBallY']
        for p in params:
            await ws.send(json.dumps({
                'type': 'parameter',
                'data': {'id': p, 'value': 0.0}
            }))
            await ws.recv()
        print('✅ 姿态已重置')

asyncio.run(reset())
"""
    subprocess.run([venv_python, "-c", reset_script])

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python mouse_follow_ctl.py [start|stop|reset]")
        sys.exit(1)
    
    cmd = sys.argv[1]
    if cmd == "start":
        start_follow()
    elif cmd == "stop":
        stop_follow()
    elif cmd == "reset":
        reset_pose()
    else:
        print(f"未知命令: {cmd}")
        print("Usage: python mouse_follow_ctl.py [start|stop|reset]")
