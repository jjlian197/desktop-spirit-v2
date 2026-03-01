#!/usr/bin/env python3
"""
WebSocket Server - Remote control interface for Sherry Sprite
Fixed for proper asyncio event loop handling on macOS
"""

import asyncio
import json
import threading
import time
from typing import Optional

import websockets
from websockets.server import WebSocketServerProtocol
from loguru import logger
from src.core.lip_sync_websocket import LipSyncWebSocketBroadcaster# Import TTS Manager

try:
    from src.core.tts_manager import TTSManager, get_tts_manager
    HAS_TTS = True
except ImportError:
    HAS_TTS = False
    logger.warning("TTS Manager not available")


class WebSocketServer:
    """WebSocket server for controlling Sherry Sprite"""

    def __init__(self, sprite_window, host: str = "127.0.0.1", port: int = 8765):
        self.sprite_window = sprite_window
        self.host = host
        self.port = port

        self.server = None
        self.loop = None
        self.thread = None
        self.clients = set()
        self._running = False
        
        # 🚨 【触觉反馈】跨线程消息队列
        self._message_queue = asyncio.Queue()
        
        self.tts_manager: Optional[TTSManager] = None
        if HAS_TTS:
            try:
                self.tts_manager = get_tts_manager()
                logger.info("✅ WebSocket server: TTS manager initialized")
            except Exception as e:
                logger.error(f"Failed to initialize TTS manager: {e}")
        self.lip_sync = LipSyncWebSocketBroadcaster(self.tts_manager, self.clients, self.loop)
        self.lip_sync.start()
        
    
    def start(self):
        """Start WebSocket server in background thread"""
        self.thread = threading.Thread(target=self._run_server, daemon=True)
        self.thread.start()
        logger.info(f"WebSocket server starting on ws://{self.host}:{self.port}/sprite")

    def stop(self):
        """Stop WebSocket server"""
        self._running = False
        # Give it a moment to shut down gracefully
        if self.thread:
            self.thread.join(timeout=2)
        logger.info("WebSocket server stopped")

    def _run_server(self):
        """Run the WebSocket server"""
        self._running = True

        async def run():
            # 🚨 保存事件循环引用（供线程安全广播使用）
            self.loop = asyncio.get_running_loop()
            
            try:
                # Create server without subprotocols (simpler and more compatible)
                self.server = await websockets.serve(
                    self._handle_client,
                    self.host,
                    self.port,
                    ping_interval=20,
                    ping_timeout=10
                )

                logger.info(f"✅ WebSocket server ready on ws://{self.host}:{self.port}")

                # Keep running until stopped
                while self._running:
                    await asyncio.sleep(0.1)

            except Exception as e:
                logger.error(f"WebSocket server error: {e}")
            finally:
                if self.server:
                    self.server.close()
                    await self.server.wait_closed()

        # Run the async function
        try:
            asyncio.run(run())
        except Exception as e:
            logger.error(f"WebSocket server thread error: {e}")

    async def _handle_client(self, websocket: WebSocketServerProtocol):
        """Handle WebSocket client connection"""
        
        logger.info(f"Client connected: {websocket.remote_address}")
        self.clients.add(websocket)
        
        try:
            async for message in websocket:
                await self._process_message(websocket, message)
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Client disconnected: {websocket.remote_address}")
        except Exception as e:
            logger.error(f"Client error: {e}")
        finally:
            self.clients.discard(websocket)

    async def _process_message(self, websocket: WebSocketServerProtocol, message: str):
        """Process incoming WebSocket message"""

        try:
            data = json.loads(message)
            msg_type = data.get("type")
            msg_data = data.get("data", {})

            logger.debug(f"Received {msg_type}: {msg_data}")

            if msg_type == "expression":
                await self._handle_expression(msg_data, websocket)
            elif msg_type == "motion":
                await self._handle_motion(msg_data, websocket)
            elif msg_type == "parameter":
                await self._handle_parameter(msg_data, websocket)
            elif msg_type == "parameter_batch":
                await self._handle_parameter_batch(msg_data, websocket)
            elif msg_type == "look_at":
                await self._handle_look_at(msg_data, websocket)
            elif msg_type == "background":
                await self._handle_background(msg_data, websocket)
            elif msg_type == "message":
                await self._handle_message(msg_data, websocket)
            elif msg_type == "speak":
                await self._handle_speak(msg_data, websocket)
            elif msg_type == "get_status":
                await self._handle_status(websocket)
            elif msg_type == "window":
                await self._handle_window(msg_data, websocket)
            else:
                await self._send_error(websocket, f"Unknown message type: {msg_type}")

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON: {e}")
            await self._send_error(websocket, "Invalid JSON")
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            await self._send_error(websocket, str(e))

    async def _handle_expression(self, data: dict, websocket: WebSocketServerProtocol):
        """Handle expression change request"""
        name = data.get("name", "normal")
        logger.info(f"Handling expression request: {name}")

        # Get the live2d view
        live2d_view = self.sprite_window.live2d_view
        
        # Check if the expression exists in live2d_view
        actual_name = None
        available = []
        if live2d_view:
            if hasattr(live2d_view, 'get_available_expressions'):
                available = live2d_view.get_available_expressions()
            
            # 🚨 直接查找原始名称，不做映射
            if hasattr(live2d_view, 'find_expression'):
                actual_name = live2d_view.find_expression(name)
                logger.info(f"find_expression('{name}') returned '{actual_name}'")

        if not actual_name:
            await self._send_error(websocket, f"Expression '{name}' not found. Available: {available[:10]}...")
            logger.warning(f"❌ Expression not found: {name}")
            return

        # Call set_expression on sprite_window (thread-safe)
        from PyQt6.QtCore import QMetaObject, Qt, Q_ARG
        QMetaObject.invokeMethod(
            self.sprite_window,
            "set_expression",
            Qt.ConnectionType.QueuedConnection,
            Q_ARG(str, name)
        )

        await self._send_response(websocket, "expression_set", {
            "requested_name": name,
            "actual_name": actual_name,
            "available_expressions": available[:20]
        })
        logger.info(f"✅ Expression request processed: {name} -> {actual_name}")

    async def _handle_motion(self, data: dict, websocket: WebSocketServerProtocol):
        """Handle motion trigger request"""
        group = data.get("group", "tap")
        index = data.get("index", 0)
        priority = data.get("priority", 2)

        from PyQt6.QtCore import QMetaObject, Qt, Q_ARG
        QMetaObject.invokeMethod(
            self.sprite_window,
            "trigger_motion",
            Qt.ConnectionType.QueuedConnection,
            Q_ARG(str, group),
            Q_ARG(int, index)
        )

        await self._send_response(websocket, "motion_triggered", {"group": group, "index": index})
        logger.info(f"Motion triggered: {group}[{index}]")

    async def _handle_parameter(self, data: dict, websocket: WebSocketServerProtocol):
        """Handle parameter set request (直接设置 Live2D 参数)"""
        param_id = data.get("id", data.get("param_id", ""))
        value = data.get("value", 0.0)
        
        if not param_id:
            await self._send_error(websocket, "Parameter ID is required")
            return
        
        # Get the live2d view
        live2d_view = self.sprite_window.live2d_view
        if not live2d_view or not hasattr(live2d_view, 'set_parameter'):
            await self._send_error(websocket, "Live2D view not available")
            return
        
        # 尝试获取当前值
        current_value = live2d_view.get_parameter(param_id)
        
        # 调用 set_parameter 方法
        from PyQt6.QtCore import QMetaObject, Qt, Q_ARG
        QMetaObject.invokeMethod(
            self.sprite_window,
            "set_parameter",
            Qt.ConnectionType.QueuedConnection,
            Q_ARG(str, param_id),
            Q_ARG(float, float(value))
        )
        
        await self._send_response(websocket, "parameter_set", {
            "param_id": param_id,
            "requested_value": value,
            "previous_value": current_value
        })
        logger.info(f"✅ Parameter set: {param_id} = {value} (was: {current_value})")

    async def _handle_parameter_batch(self, data: dict, websocket: WebSocketServerProtocol):
        """批量设置参数 - 高效处理鼠标跟随"""
        params = data.get("params", {})
        
        if not params:
            return
        
        live2d_view = self.sprite_window.live2d_view
        if not live2d_view or not hasattr(live2d_view, 'set_parameter'):
            return
        
        # 批量设置参数
        for param_id, value in params.items():
            from PyQt6.QtCore import QMetaObject, Qt, Q_ARG
            QMetaObject.invokeMethod(
                self.sprite_window,
                "set_parameter",
                Qt.ConnectionType.QueuedConnection,
                Q_ARG(str, param_id),
                Q_ARG(float, float(value))
            )
        
        # 降低日志频率，只在需要时输出
        # logger.debug(f"✅ Parameters batch set: {len(params)} params")

    async def _handle_look_at(self, data: dict, websocket: WebSocketServerProtocol):
        """Handle look_at request - 控制眼神看向指定位置"""
        x = data.get("x", 0.0)
        y = data.get("y", 0.0)
        
        from PyQt6.QtCore import QMetaObject, Qt, Q_ARG
        QMetaObject.invokeMethod(
            self.sprite_window,
            "look_at",
            Qt.ConnectionType.QueuedConnection,
            Q_ARG(float, float(x)),
            Q_ARG(float, float(y))
        )
        
        await self._send_response(websocket, "looking_at", {"x": x, "y": y})
        logger.info(f"👀 Look at: ({x}, {y})")

    async def _handle_background(self, data: dict, websocket: WebSocketServerProtocol):
        """Handle background change request"""
        bg_type = data.get("type", "transparent")
        bg_path = data.get("path")
        
        from PyQt6.QtCore import QMetaObject, Qt, Q_ARG
        
        # 🚨 【修正】统一调用 set_background，并根据逻辑构造参数
        final_cmd = bg_type
        if bg_type == "image" and bg_path:
            final_cmd = f"image:{bg_path}"
        
        QMetaObject.invokeMethod(
            self.sprite_window,
            "set_background",
            Qt.ConnectionType.QueuedConnection,
            Q_ARG(str, final_cmd)
        )
            
        await self._send_response(websocket, "background_set", {"type": final_cmd})
        logger.info(f"✅ Background request processed: {final_cmd}")
    

    async def _handle_message(self, data: dict, websocket: WebSocketServerProtocol):
        """Handle message display request"""
        text = data.get("text", "")
        duration = data.get("duration", 5000)

        from PyQt6.QtCore import QMetaObject, Qt, Q_ARG
        QMetaObject.invokeMethod(
            self.sprite_window,
            "show_message",
            Qt.ConnectionType.QueuedConnection,
            Q_ARG(str, text),
            Q_ARG(int, duration)
        )

        await self._send_response(websocket, "message_shown", {"text": text})
        logger.info(f"Message shown: {text}")

    async def _handle_speak(self, data: dict, websocket: WebSocketServerProtocol):
        """Handle TTS/speak request using TTSManager"""
        text = data.get("text", "")
        voice = data.get("voice")  # Optional voice override
        provider = data.get("provider")  # Optional provider override

        if not text:
            await self._send_error(websocket, "Text is required for speak command")
            return

        # Show message bubble
        from PyQt6.QtCore import QMetaObject, Qt, Q_ARG
        QMetaObject.invokeMethod(
            self.sprite_window,
            "show_message",
            Qt.ConnectionType.QueuedConnection,
            Q_ARG(str, text),
            Q_ARG(int, 5000)
        )

        # Use TTS manager for speech
        if self.tts_manager and HAS_TTS:
            try:
                # Switch provider if requested
                if provider and provider != self.tts_manager.current_provider.name.lower():
                    available = self.tts_manager.get_available_providers()
                    if provider in available:
                        self.tts_manager.set_provider(provider)
                        logger.info(f"🎙️ Switched TTS provider to: {provider}")

                # Generate and play speech
                result = await self.tts_manager.speak(text, voice)

                if result.success:
                    await self._send_response(websocket, "speak_completed", {
                        "text": text,
                        "provider": self.tts_manager.current_provider.name,
                        "duration_ms": result.duration_ms,
                        "audio_path": result.audio_path
                    })
                    logger.info(f"✅ Speak completed: {text[:50]}...")
                else:
                    await self._send_error(websocket, f"TTS failed: {result.error}")
                    logger.error(f"❌ TTS failed: {result.error}")

            except Exception as e:
                logger.error(f"❌ TTS error: {e}")
                await self._send_error(websocket, f"TTS error: {str(e)}")
        else:
            # Fallback to system say command
            logger.warning("TTS manager not available, using fallback say command")
            import subprocess
            try:
                subprocess.run(["say", text], check=True, capture_output=True)
                await self._send_response(websocket, "speak_completed", {
                    "text": text,
                    "provider": "fallback_say",
                    "note": "TTS manager not available, using system say"
                })
            except Exception as e:
                logger.warning(f"Fallback TTS failed: {e}")
                await self._send_error(websocket, f"TTS unavailable: {str(e)}")

    async def _handle_status(self, websocket: WebSocketServerProtocol):
        """Handle status request"""
        try:
            # Get available expressions from live2d view
            expressions = []
            if self.sprite_window.live2d_view and hasattr(self.sprite_window.live2d_view, 'get_available_expressions'):
                expressions = self.sprite_window.live2d_view.get_available_expressions()

            status = {
                "state": "idle",
                "expression": self.sprite_window.live2d_view.current_expression if self.sprite_window.live2d_view else "normal",
                "position": {
                    "x": self.sprite_window.x(),
                    "y": self.sprite_window.y()
                },
                "connected_clients": len(self.clients),
                "available_expressions": expressions[:20],  # Return first 20
                "total_expressions": len(expressions)
            }
            await self._send_response(websocket, "status", status)
        except Exception as e:
            logger.error(f"Status error: {e}")
            await self._send_error(websocket, "Failed to get status")

    async def _handle_window(self, data: dict, websocket: WebSocketServerProtocol):
        """Handle window control request"""
        action = data.get("action")

        from PyQt6.QtCore import QMetaObject, Qt, Q_ARG

        try:
            if action == "move":
                x = data.get("x", self.sprite_window.x())
                y = data.get("y", self.sprite_window.y())
                QMetaObject.invokeMethod(
                    self.sprite_window,
                    "set_position",
                    Qt.ConnectionType.QueuedConnection,
                    Q_ARG(int, x),
                    Q_ARG(int, y)
                )
            elif action == "opacity":
                opacity = data.get("opacity", 1.0)
                QMetaObject.invokeMethod(
                    self.sprite_window,
                    "set_opacity",
                    Qt.ConnectionType.QueuedConnection,
                    Q_ARG(float, opacity)
                )
            elif action == "hide":
                QMetaObject.invokeMethod(
                    self.sprite_window,
                    "hide",
                    Qt.ConnectionType.QueuedConnection
                )
            elif action == "show":
                QMetaObject.invokeMethod(
                    self.sprite_window,
                    "show",
                    Qt.ConnectionType.QueuedConnection
                )

            await self._send_response(websocket, "window_updated", {"action": action})
        except Exception as e:
            logger.error(f"Window control error: {e}")
            await self._send_error(websocket, f"Failed to {action} window")

    async def _send_response(self, websocket: WebSocketServerProtocol, msg_type: str, data: dict):
        """Send success response"""
        try:
            response = {
                "type": msg_type,
                "data": data,
                "success": True
            }
            await websocket.send(json.dumps(response))
        except Exception as e:
            logger.error(f"Failed to send response: {e}")

    async def _send_error(self, websocket: WebSocketServerProtocol, error: str):
        """Send error response"""
        try:
            response = {
                "type": "error",
                "data": {"message": error},
                "success": False
            }
            await websocket.send(json.dumps(response))
        except Exception as e:
            logger.error(f"Failed to send error: {e}")

    def broadcast_sync(self, msg_type: str, data: dict):
        """🚨 【触觉反馈】线程安全的广播方法（供 Qt 线程调用）"""
        if self.loop and self.loop.is_running():
            # 使用 call_soon_threadsafe 将任务提交到 asyncio 事件循环
            future = asyncio.run_coroutine_threadsafe(
                self.broadcast(msg_type, data), 
                self.loop
            )
            try:
                future.result(timeout=1.0)  # 等待最多1秒
            except Exception as e:
                logger.debug(f"Broadcast sync error: {e}")
        else:
            logger.warning("WebSocket loop not running, cannot broadcast")

    async def broadcast(self, msg_type: str, data: dict):
        """Broadcast message to all connected clients"""
        if not self.clients:
            logger.debug("No clients connected, skipping broadcast")
            return

        message = json.dumps({"type": msg_type, "data": data})
        logger.info(f"📢 Broadcasting to {len(self.clients)} clients: {msg_type}")
        disconnected = set()

        for client in self.clients:
            try:
                await client.send(message)
                logger.debug(f"Message sent to {client.remote_address}")
            except websockets.exceptions.ConnectionClosed:
                disconnected.add(client)
            except Exception as e:
                logger.error(f"Broadcast error: {e}")
                disconnected.add(client)

        # Clean up disconnected clients
        if disconnected:
            self.clients -= disconnected
            logger.info(f"Cleaned up {len(disconnected)} disconnected clients")
