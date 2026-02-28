#!/usr/bin/env python3
"""
Sherry Desktop Sprite - Test Client
Simple WebSocket client for testing the sprite API
"""

import asyncio
import websockets
import json
import sys


async def test_expression():
    """Test expression changes"""
    uri = "ws://127.0.0.1:8765/sprite"
    
    async with websockets.connect(uri) as ws:
        print("Testing expressions...")
        
        expressions = ["happy", "love", "surprised", "sad", "normal"]
        
        for expr in expressions:
            await ws.send(json.dumps({
                "type": "expression",
                "data": {"name": expr}
            }))
            response = await ws.recv()
            print(f"  Set expression '{expr}': {response}")
            await asyncio.sleep(1)


async def test_message():
    """Test message bubble"""
    uri = "ws://127.0.0.1:8765/sprite"
    
    async with websockets.connect(uri) as ws:
        print("\nTesting message bubble...")
        
        messages = [
            "Meow~ Master! 💜",
            "Sherry is here to help!",
            "What can I do for you today?"
        ]
        
        for msg in messages:
            await ws.send(json.dumps({
                "type": "message",
                "data": {"text": msg, "duration": 3000}
            }))
            response = await ws.recv()
            print(f"  Message sent: {msg}")
            await asyncio.sleep(2)


async def test_speak():
    """Test TTS"""
    uri = "ws://127.0.0.1:8765/sprite"
    
    async with websockets.connect(uri) as ws:
        print("\nTesting speech...")
        
        await ws.send(json.dumps({
            "type": "speak",
            "data": {"text": "Hello Master! Sherry is ready to serve you!"}
        }))
        response = await ws.recv()
        print(f"  Speech completed")


async def test_status():
    """Test status query"""
    uri = "ws://127.0.0.1:8765/sprite"
    
    async with websockets.connect(uri) as ws:
        print("\nTesting status query...")
        
        await ws.send(json.dumps({
            "type": "get_status",
            "data": {}
        }))
        response = await ws.recv()
        data = json.loads(response)
        print(f"  Status: {json.dumps(data, indent=2)}")


async def test_motion():
    """Test motion trigger"""
    uri = "ws://127.0.0.1:8765/sprite"
    
    async with websockets.connect(uri) as ws:
        print("\nTesting motions...")
        
        motions = [
            ("tap", 0),
            ("idle", 0),
            ("greeting", 0)
        ]
        
        for group, idx in motions:
            await ws.send(json.dumps({
                "type": "motion",
                "data": {"group": group, "index": idx}
            }))
            response = await ws.recv()
            print(f"  Motion triggered: {group}[{idx}]")
            await asyncio.sleep(1)


async def interactive_mode():
    """Interactive command mode"""
    uri = "ws://127.0.0.1:8765/sprite"
    
    print("\n🐱 Sherry Interactive Test Client")
    print("Commands:")
    print("  expr <name>    - Set expression (happy, sad, love, etc.)")
    print("  msg <text>     - Show message bubble")
    print("  speak <text>   - Text to speech")
    print("  motion <name>  - Trigger motion")
    print("  status          - Get status")
    print("  quit            - Exit")
    print()
    
    async with websockets.connect(uri) as ws:
        while True:
            try:
                cmd = input("Sherry> ").strip()
                
                if not cmd:
                    continue
                
                parts = cmd.split(maxsplit=1)
                action = parts[0].lower()
                arg = parts[1] if len(parts) > 1 else ""
                
                if action == "quit":
                    break
                elif action == "expr":
                    await ws.send(json.dumps({
                        "type": "expression",
                        "data": {"name": arg or "normal"}
                    }))
                elif action == "msg":
                    await ws.send(json.dumps({
                        "type": "message",
                        "data": {"text": arg or "Hello!", "duration": 5000}
                    }))
                elif action == "speak":
                    await ws.send(json.dumps({
                        "type": "speak",
                        "data": {"text": arg or "Hello Master!"}
                    }))
                elif action == "motion":
                    await ws.send(json.dumps({
                        "type": "motion",
                        "data": {"group": arg or "tap", "index": 0}
                    }))
                elif action == "status":
                    await ws.send(json.dumps({
                        "type": "get_status",
                        "data": {}
                    }))
                else:
                    print(f"Unknown command: {action}")
                    continue
                
                # Receive response
                response = await asyncio.wait_for(ws.recv(), timeout=5.0)
                data = json.loads(response)
                
                if data.get("success"):
                    print(f"✅ {data.get('type')}")
                else:
                    print(f"❌ Error: {data.get('data', {}).get('message', 'Unknown')}")
                    
            except asyncio.TimeoutError:
                print("⚠️  Timeout waiting for response")
            except Exception as e:
                print(f"❌ Error: {e}")


async def main():
    """Main test runner"""
    if len(sys.argv) < 2:
        print("Usage: python test_client.py [all|expression|message|speak|status|motion|interactive]")
        print()
        print("Examples:")
        print("  python test_client.py all          - Run all tests")
        print("  python test_client.py interactive  - Interactive mode")
        print("  python test_client.py message      - Test messages only")
        sys.exit(1)
    
    test = sys.argv[1]
    
    try:
        if test == "all":
            await test_expression()
            await test_message()
            await test_motion()
            await test_speak()
            await test_status()
        elif test == "expression":
            await test_expression()
        elif test == "message":
            await test_message()
        elif test == "speak":
            await test_speak()
        elif test == "status":
            await test_status()
        elif test == "motion":
            await test_motion()
        elif test == "interactive":
            await interactive_mode()
        else:
            print(f"Unknown test: {test}")
            sys.exit(1)
            
        print("\n✅ Tests completed!")
        
    except ConnectionRefusedError:
        print("❌ Could not connect to Sherry Sprite!")
        print("   Make sure the sprite is running: python src/main.py")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
