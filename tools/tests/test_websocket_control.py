#!/usr/bin/env python3
"""
测试 WebSocket 控制 Live2D 参数的客户端脚本
用于验证参数控制是否正常工作
"""

import asyncio
import json
import websockets
import sys

async def test_connection():
    """测试 WebSocket 连接和参数控制"""
    uri = "ws://127.0.0.1:8765"
    
    try:
        async with websockets.connect(uri) as ws:
            print("✅ 已连接到 WebSocket 服务器")
            
            # 1. 获取当前状态
            print("\n📊 获取当前状态...")
            await ws.send(json.dumps({
                "type": "get_status",
                "data": {}
            }))
            response = await ws.recv()
            print(f"状态响应: {response}")
            
            # 2. 测试设置参数 - 转头
            print("\n🔄 测试转头动作 (ParamAngleX)...")
            await ws.send(json.dumps({
                "type": "parameter",
                "data": {
                    "id": "ParamAngleX",
                    "value": 15.0
                }
            }))
            response = await ws.recv()
            print(f"转头响应: {response}")
            
            await asyncio.sleep(1)
            
            # 3. 测试设置参数 - 转回
            print("\n🔄 转回中心...")
            await ws.send(json.dumps({
                "type": "parameter",
                "data": {
                    "id": "ParamAngleX",
                    "value": 0.0
                }
            }))
            response = await ws.recv()
            print(f"转回响应: {response}")
            
            await asyncio.sleep(0.5)
            
            # 4. 测试表情 - 星星眼
            print("\n⭐ 测试星星眼表情...")
            await ws.send(json.dumps({
                "type": "expression",
                "data": {
                    "name": "happy"
                }
            }))
            response = await ws.recv()
            print(f"表情响应: {response}")
            
            await asyncio.sleep(2)
            
            # 5. 恢复正常表情
            print("\n😊 恢复正常表情...")
            await ws.send(json.dumps({
                "type": "expression",
                "data": {
                    "name": "normal"
                }
            }))
            response = await ws.recv()
            print(f"恢复响应: {response}")
            
            # 6. 测试功能按键 - 比心
            print("\n💕 测试比心手势...")
            await ws.send(json.dumps({
                "type": "parameter",
                "data": {
                    "id": "Key32",
                    "value": 1.0
                }
            }))
            response = await ws.recv()
            print(f"比心响应: {response}")
            
            await asyncio.sleep(2)
            
            # 关闭比心
            await ws.send(json.dumps({
                "type": "parameter",
                "data": {
                    "id": "Key32",
                    "value": 0.0
                }
            }))
            
            print("\n✅ 所有测试完成!")
            
    except Exception as e:
        print(f"❌ 错误: {e}")
        sys.exit(1)

async def test_parameter_control(param_id: str, value: float):
    """单独测试某个参数"""
    uri = "ws://127.0.0.1:8765"
    
    async with websockets.connect(uri) as ws:
        print(f"设置参数 {param_id} = {value}")
        await ws.send(json.dumps({
            "type": "parameter",
            "data": {
                "id": param_id,
                "value": value
            }
        }))
        response = await ws.recv()
        data = json.loads(response)
        if data.get("success"):
            print(f"✅ 成功! 之前值: {data.get('data', {}).get('previous_value')}")
        else:
            print(f"❌ 失败: {data.get('data', {}).get('message')}")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="测试桌面精灵 WebSocket 控制")
    parser.add_argument("--param", help="参数ID (如 ParamAngleX)")
    parser.add_argument("--value", type=float, help="参数值")
    parser.add_argument("--test-all", action="store_true", help="运行所有测试")
    
    args = parser.parse_args()
    
    if args.test_all:
        asyncio.run(test_connection())
    elif args.param and args.value is not None:
        asyncio.run(test_parameter_control(args.param, args.value))
    else:
        # 默认运行完整测试
        asyncio.run(test_connection())
