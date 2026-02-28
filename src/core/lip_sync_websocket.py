#!/usr/bin/env python3
"""
Lip Sync WebSocket Module - Standalone module for real-time lip sync broadcasting

This module provides a reusable component that can be integrated into the existing
WebSocket server to broadcast lip sync data during TTS playback.

Usage:
    from src.core.lip_sync_websocket import LipSyncWebSocketBroadcaster
    
    # In your WebSocketServer.__init__:
    self.lip_sync = LipSyncWebSocketBroadcaster(self.tts_manager, self.clients, self.loop)
    self.lip_sync.start()
"""

import asyncio
import json
import time
from typing import Optional, Set, Callable
from dataclasses import dataclass

from loguru import logger

try:
    from src.core.tts_manager import TTSManager
    HAS_TTS = True
except ImportError:
    HAS_TTS = False
    TTSManager = None


@dataclass
class LipSyncFrame:
    """A single lip sync frame data"""
    param_id: str      # Live2D parameter ID (e.g., "ParamMouthOpenY")
    value: float       # Value 0.0 - 1.0
    timestamp: float   # Unix timestamp
    duration_ms: int   # Frame duration in milliseconds


class LipSyncWebSocketBroadcaster:
    """
    Broadcasts real-time lip sync data to WebSocket clients during TTS playback.
    
    Features:
    - Connects to TTSManager's lip_sync_frame signal
    - Broadcasts ParamMouthOpenY values to all connected WebSocket clients
    - Configurable smoothing and frame rate
    - Can disable local Live2D lip sync when client wants to handle it
    """
    
    def __init__(
        self,
        tts_manager: TTSManager,
        clients: Set,
        loop: asyncio.AbstractEventLoop,
        param_id: str = "ParamMouthOpenY",
        smoothing: float = 0.3
    ):
        """
        Initialize the lip sync broadcaster.
        
        Args:
            tts_manager: The TTSManager instance to connect to
            clients: Set of connected WebSocket clients (shared with main server)
            loop: The asyncio event loop to use for broadcasting
            param_id: The Live2D parameter ID for mouth opening (default: ParamMouthOpenY)
            smoothing: Smoothing factor for mouth movement (0.0 - 1.0, higher = more responsive)
        """
        self.tts_manager = tts_manager
        self.clients = clients
        self.loop = loop
        self.param_id = param_id
        self.smoothing = smoothing
        
        self._connected = False
        self._current_value = 0.0
        self._smoothed_value = 0.0
        self._last_broadcast_time = 0.0
        self._min_broadcast_interval = 0.016  # ~60fps max
        
    def start(self):
        """Start listening to TTS lip sync signals"""
        if not HAS_TTS or not self.tts_manager:
            logger.warning("TTS manager not available, lip sync broadcasting disabled")
            return
            
        if self._connected:
            return
            
        try:
            # Connect to the lip_sync_frame signal from TTS manager
            self.tts_manager.lip_sync_frame.connect(self._on_lip_sync_frame)
            self._connected = True
            logger.info(f"✅ Lip sync broadcaster started (param: {self.param_id})")
        except Exception as e:
            logger.error(f"Failed to connect lip sync signal: {e}")
    
    def stop(self):
        """Stop listening to TTS lip sync signals"""
        if not self._connected or not self.tts_manager:
            return
            
        try:
            self.tts_manager.lip_sync_frame.disconnect(self._on_lip_sync_frame)
            self._connected = False
            logger.info(" Lip sync broadcaster stopped")
        except Exception as e:
            logger.debug(f"Error disconnecting lip sync signal: {e}")
    
    def _on_lip_sync_frame(self, mouth_open: float):
        """
        Handle incoming lip sync frame from TTS manager.
        Called ~30 times per second during TTS playback.
        
        Args:
            mouth_open: Normalized mouth opening value (0.0 = closed, 1.0 = fully open)
        """
        self._current_value = mouth_open
        
        # Apply smoothing
        self._smoothed_value += (mouth_open - self._smoothed_value) * self.smoothing
        
        # Rate limiting - don't broadcast too frequently
        current_time = time.time()
        if current_time - self._last_broadcast_time < self._min_broadcast_interval:
            return
        self._last_broadcast_time = current_time
        
        # Schedule broadcast in the event loop (thread-safe)
        if self.loop and self.clients:
            try:
                asyncio.run_coroutine_threadsafe(
                    self._broadcast_frame(),
                    self.loop
                )
            except Exception as e:
                logger.debug(f"Failed to schedule lip sync broadcast: {e}")
    
    async def _broadcast_frame(self):
        """Broadcast the current lip sync frame to all connected clients"""
        if not self.clients:
            return
        
        # Build the lip sync message
        message = {
            "type": "lip_sync",
            "data": {
                "param_id": self.param_id,
                "value": round(self._smoothed_value, 3),
                "raw_value": round(self._current_value, 3),
                "timestamp": time.time(),
                "smoothing": self.smoothing
            },
            "success": True
        }
        
        json_message = json.dumps(message)
        disconnected = set()
        
        # Send to all connected clients
        for client in self.clients:
            try:
                await client.send(json_message)
            except Exception as e:
                # Client disconnected or error
                disconnected.add(client)
        
        # Remove disconnected clients
        if disconnected:
            self.clients -= disconnected
    
    def set_smoothing(self, smoothing: float):
        """Update the smoothing factor (0.0 - 1.0)"""
        self.smoothing = max(0.0, min(1.0, smoothing))
    
    def get_current_value(self) -> float:
        """Get the current smoothed lip sync value"""
        return self._smoothed_value


class LipSyncController:
    """
    Higher-level controller for managing lip sync across local Live2D and remote clients.
    
    This allows clients to choose whether the server handles lip sync (local Live2D)
    or the client handles it (via WebSocket events).
    """
    
    def __init__(
        self,
        tts_manager: TTSManager,
        live2d_view=None,
        broadcaster: Optional[LipSyncWebSocketBroadcaster] = None
    ):
        """
        Initialize the lip sync controller.
        
        Args:
            tts_manager: The TTSManager instance
            live2d_view: The Live2D view widget (for local lip sync)
            broadcaster: The WebSocket broadcaster (for remote lip sync)
        """
        self.tts_manager = tts_manager
        self.live2d_view = live2d_view
        self.broadcaster = broadcaster
        
        self._local_enabled = True
        self._remote_enabled = True
    
    def enable_local(self, enabled: bool = True):
        """Enable/disable local Live2D lip sync"""
        self._local_enabled = enabled
        if self.live2d_view and hasattr(self.live2d_view, 'set_lip_sync_enabled'):
            self.live2d_view.set_lip_sync_enabled(enabled)
    
    def enable_remote(self, enabled: bool = True):
        """Enable/disable remote WebSocket lip sync broadcasting"""
        self._remote_enabled = enabled
        if self.broadcaster:
            if enabled:
                self.broadcaster.start()
            else:
                self.broadcaster.stop()
    
    def configure(self, local: bool = True, remote: bool = True):
        """Configure both local and remote lip sync"""
        self.enable_local(local)
        self.enable_remote(remote)
        logger.info(f"🎭 Lip sync configured - Local: {local}, Remote: {remote}")


# Integration helper for existing WebSocketServer
def integrate_lip_sync(websocket_server, tts_manager, live2d_view=None):
    """
    Helper function to integrate lip sync broadcasting into an existing WebSocketServer.
    
    Usage in WebSocketServer.__init__:
        from src.core.lip_sync_websocket import integrate_lip_sync
        integrate_lip_sync(self, self.tts_manager, self.sprite_window.live2d_view)
    
    Args:
        websocket_server: The WebSocketServer instance
        tts_manager: The TTSManager instance
        live2d_view: Optional Live2D view for local lip sync control
    """
    if not HAS_TTS or not tts_manager:
        logger.warning("Cannot integrate lip sync: TTS manager not available")
        return
    
    # Wait for the server loop to be ready
    def setup_broadcaster():
        if hasattr(websocket_server, 'loop') and websocket_server.loop:
            broadcaster = LipSyncWebSocketBroadcaster(
                tts_manager=tts_manager,
                clients=websocket_server.clients,
                loop=websocket_server.loop
            )
            broadcaster.start()
            
            # Store reference on the server
            websocket_server.lip_sync_broadcaster = broadcaster
            
            # Create controller if live2d_view is provided
            if live2d_view:
                websocket_server.lip_sync_controller = LipSyncController(
                    tts_manager=tts_manager,
                    live2d_view=live2d_view,
                    broadcaster=broadcaster
                )
            
            logger.info("✅ Lip sync integration complete")
    
    # Schedule setup after server starts
    import threading
    timer = threading.Timer(1.0, setup_broadcaster)
    timer.daemon = True
    timer.start()
