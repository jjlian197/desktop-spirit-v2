#!/usr/bin/env python3
"""
Sherry Desktop Sprite - 水印去除脚本
通过 WebSocket 直接设置 Open_EyeMask4 参数
"""

import asyncio
import json
import websockets
import sys

async def remove_watermark():
    """通过 WebSocket 发送去水印命令"""
    uri = "ws://127.0.0.1:8765/sprite"
    
    try:
        async with websockets.connect(uri) as websocket:
            print("🔗 已连接到 Sherry Sprite")
            
            # 方法 1: 尝试使用 expression
            print("\n📌 方法 1: 发送 expression 命令 '去水印'")
            await websocket.send(json.dumps({
                "type": "expression",
                "data": {"name": "去水印"}
            }))
            
            response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            print(f"   响应: {response}")
            
            await asyncio.sleep(1)
            
            # 方法 2: 直接设置参数 (推荐方法)
            print("\n📌 方法 2: 直接设置参数 Open_EyeMask4 = -1.0")
            await websocket.send(json.dumps({
                "type": "parameter",
                "data": {"id": "Open_EyeMask4", "value": -1.0}
            }))
            
            response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            print(f"   响应: {response}")
            
            # 等待一下让参数生效
            await asyncio.sleep(0.5)
            
            # 再次设置确保生效
            print("\n📌 方法 3: 再次设置参数确保生效")
            await websocket.send(json.dumps({
                "type": "parameter",
                "data": {"id": "Open_EyeMask4", "value": -1.0}
            }))
            
            response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            print(f"   响应: {response}")
            
            print("\n✅ 水印去除命令已发送！")
            print("💡 请观察精灵窗口，水印应该已经消失")
            
    except websockets.exceptions.ConnectionRefused:
        print("❌ 无法连接到 Sherry Sprite")
        print("   请确保 sprite 正在运行: python3 src/main.py")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 错误: {e}")
        sys.exit(1)

async def check_status():
    """检查精灵状态"""
    uri = "ws://127.0.0.1:8765/sprite"
    
    try:
        async with websockets.connect(uri) as websocket:
            await websocket.send(json.dumps({
                "type": "get_status"
            }))
            
            response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            data = json.loads(response)
            
            print("📊 精灵状态:")
            print(json.dumps(data, indent=2, ensure_ascii=False))
            
    except Exception as e:
        print(f"❌ 无法获取状态: {e}")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Sherry Desktop Sprite 水印去除工具")
    parser.add_argument("--status", action="store_true", help="检查精灵状态")
    parser.add_argument("--param", help="设置任意参数，格式: '参数名=值'")
    
    args = parser.parse_args()
    
    if args.status:
        asyncio.run(check_status())
    elif args.param:
        # 解析参数格式: "ParamName=1.0"
        try:
            param_id, value = args.param.split("=")
            value = float(value)
            
            async def set_custom_param():
                uri = "ws://127.0.0.1:8765/sprite"
                async with websockets.connect(uri) as websocket:
                    await websocket.send(json.dumps({
                        "type": "parameter",
                        "data": {"id": param_id, "value": value}
                    }))
                    response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    print(f"✅ 设置完成: {response}")
            
            asyncio.run(set_custom_param())
        except ValueError:
            print("❌ 参数格式错误，请使用: '参数名=值'")
            print("   例如: --param 'Open_EyeMask4=-1.0'")
            sys.exit(1)
    else:
        asyncio.run(remove_watermark())
