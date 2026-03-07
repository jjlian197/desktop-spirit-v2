#!/usr/bin/env python3
"""
HTTP API Server - RESTful interface for Sherry Sprite
Supports: background change, status query, TTS control, etc.
"""

import json
import asyncio
from typing import Optional
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot, QMetaObject, Qt, Q_ARG
from loguru import logger

# Try to import TTS Manager
try:
    from src.core.tts_manager import TTSManager, get_tts_manager
    HAS_TTS = True
except ImportError:
    HAS_TTS = False
    logger.warning("TTS Manager not available for HTTP server")


class HTTPRequestHandler:
    """HTTP request handler for Sherry API"""
    
    def __init__(self, sprite_window):
        self.sprite_window = sprite_window
        self.tts_manager = None
        if HAS_TTS:
            try:
                self.tts_manager = get_tts_manager()
            except Exception as e:
                logger.warning(f"Failed to get TTS manager: {e}")
    
    async def handle_request(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """Handle HTTP request"""
        try:
            # Read request line
            request_line = await reader.readline()
            request_line = request_line.decode('utf-8').strip()
            
            if not request_line:
                return
            
            # Parse request
            parts = request_line.split()
            if len(parts) < 3:
                await self._send_error(writer, 400, "Bad Request")
                return
            
            method, path, version = parts
            
            # Read headers
            headers = {}
            while True:
                header_line = await reader.readline()
                if header_line == b'\r\n':
                    break
                key, _, value = header_line.decode('utf-8').strip().partition(':')
                headers[key.strip().lower()] = value.strip()
            
            # Read body if present
            body = ""
            content_length = int(headers.get('content-length', 0))
            if content_length > 0:
                body_data = await reader.read(content_length)
                body = body_data.decode('utf-8')
            
            # Route request
            parsed_path = urlparse(path)
            route = parsed_path.path
            query = parse_qs(parsed_path.query)
            
            logger.debug(f"HTTP {method} {route}")
            
            if route == "/api/background":
                await self._handle_background(method, query, body, writer)
            elif route == "/api/status":
                await self._handle_status(writer)
            elif route == "/api/expression":
                await self._handle_expression(method, query, body, writer)
            elif route == "/api/speak":
                await self._handle_speak(method, query, body, writer)
            elif route == "/api/window":
                await self._handle_window(method, query, body, writer)
            else:
                await self._send_error(writer, 404, "Not Found")
                
        except Exception as e:
            logger.error(f"HTTP request error: {e}")
            await self._send_error(writer, 500, str(e))
        finally:
            writer.close()
            await writer.wait_closed()
    
    async def _handle_background(self, method: str, query: dict, body: str, writer: asyncio.StreamWriter):
        """Handle background API"""
        if method == "GET":
            await self._send_json(writer, 200, {"success": True, "message": "Background API ready"})
            return
            
        if method != "POST":
            await self._send_error(writer, 405, "Method Not Allowed")
            return
            
        try:
            data = json.loads(body) if body else {}
            bg_type = data.get("type", "transparent")
            bg_path = data.get("path", "")
            
            # Construct command: image:path or color:value or direct type
            cmd = f"image:{bg_path}" if bg_type == "image" and bg_path else bg_path if bg_type == "color" else bg_type
            
            QMetaObject.invokeMethod(
                self.sprite_window, "set_background",
                Qt.ConnectionType.QueuedConnection, Q_ARG(str, cmd)
            )
            
            await self._send_json(writer, 200, {"success": True, "background": cmd})
            logger.info(f"✅ HTTP API: Background set to {cmd}")
            
        except Exception as e:
            await self._send_json(writer, 400, {"success": False, "error": str(e)})
    
    async def _handle_expression(self, method: str, query: dict, body: str, writer: asyncio.StreamWriter):
        """Handle expression API"""
        if method == "POST":
            try:
                data = json.loads(body) if body else {}
                expr_name = data.get("name", "normal")
                
                QMetaObject.invokeMethod(
                    self.sprite_window,
                    "set_expression",
                    Qt.ConnectionType.QueuedConnection,
                    Q_ARG(str, expr_name)
                )
                
                result = {"success": True, "expression": expr_name}
                await self._send_json(writer, 200, result)
                
            except Exception as e:
                await self._send_json(writer, 400, {"success": False, "error": str(e)})
        else:
            await self._send_error(writer, 405, "Method Not Allowed")
    
    async def _handle_speak(self, method: str, query: dict, body: str, writer: asyncio.StreamWriter):
        """Handle speak API"""
        if method == "POST":
            try:
                data = json.loads(body) if body else {}
                text = data.get("text", "")
                
                if not text:
                    await self._send_json(writer, 400, {"success": False, "error": "Text required"})
                    return
                
                # Show message bubble
                QMetaObject.invokeMethod(
                    self.sprite_window,
                    "show_message",
                    Qt.ConnectionType.QueuedConnection,
                    Q_ARG(str, text),
                    Q_ARG(int, 5000)
                )
                
                result = {"success": True, "text": text}
                await self._send_json(writer, 200, result)
                
            except Exception as e:
                await self._send_json(writer, 400, {"success": False, "error": str(e)})
        else:
            await self._send_error(writer, 405, "Method Not Allowed")
    
    async def _handle_window(self, method: str, query: dict, body: str, writer: asyncio.StreamWriter):
        """Handle window control API"""
        if method == "POST":
            try:
                data = json.loads(body) if body else {}
                action = data.get("action", "")
                
                if action == "move":
                    x = data.get("x", 0)
                    y = data.get("y", 0)
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
                
                result = {"success": True, "action": action}
                await self._send_json(writer, 200, result)
                
            except Exception as e:
                await self._send_json(writer, 400, {"success": False, "error": str(e)})
        else:
            await self._send_error(writer, 405, "Method Not Allowed")
    
    async def _handle_status(self, writer: asyncio.StreamWriter):
        """Handle status API"""
        result = {
            "success": True,
            "status": "running",
            "name": "Sherry Desktop Sprite",
            "apis": [
                "/api/background",
                "/api/status", 
                "/api/expression",
                "/api/speak",
                "/api/window"
            ]
        }
        await self._send_json(writer, 200, result)
    
    async def _send_json(self, writer: asyncio.StreamWriter, status: int, data: dict):
        """Send JSON response"""
        body = json.dumps(data, ensure_ascii=False).encode('utf-8')
        headers = [
            f"HTTP/1.1 {status} OK",
            "Content-Type: application/json; charset=utf-8",
            f"Content-Length: {len(body)}",
            "Access-Control-Allow-Origin: *",
            "Access-Control-Allow-Methods: GET, POST, OPTIONS",
            "Access-Control-Allow-Headers: Content-Type",
            "Connection: close",
            "",
            ""
        ]
        response = "\r\n".join(headers).encode('utf-8') + body
        writer.write(response)
        await writer.drain()
    
    async def _send_error(self, writer: asyncio.StreamWriter, status: int, message: str):
        """Send error response"""
        await self._send_json(writer, status, {"success": False, "error": message})


class HTTPServer:
    """HTTP API Server for Sherry Sprite"""
    
    def __init__(self, sprite_window, host: str = "127.0.0.1", port: int = 8766):
        self.sprite_window = sprite_window
        self.host = host
        self.port = port
        self.server = None
        self._running = False
        self.handler = HTTPRequestHandler(sprite_window)
    
    async def start(self):
        """Start HTTP server"""
        self._running = True
        self.server = await asyncio.start_server(
            self.handler.handle_request,
            self.host,
            self.port
        )
        logger.info(f"✅ HTTP API server ready on http://{self.host}:{self.port}")
        async with self.server:
            while self._running:
                await asyncio.sleep(0.1)
    
    def stop(self):
        """Stop HTTP server"""
        self._running = False
        if self.server:
            self.server.close()
        logger.info("HTTP server stopped")
