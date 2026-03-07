#!/usr/bin/env python3
"""
TTS Provider Base Classes
Base classes and data structures for TTS providers
This module is separate to avoid circular imports
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class TTSResult:
    """Result from TTS generation"""
    audio_path: str
    text: str
    duration_ms: float
    sample_rate: int
    success: bool
    error: Optional[str] = None


class BaseTTSProvider(ABC):
    """Base class for TTS providers"""
    
    def __init__(self, name: str):
        self.name = name
        self._initialized = False
    
    @abstractmethod
    async def speak(self, text: str, voice_id: Optional[str] = None) -> TTSResult:
        """Generate and return audio file path"""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if provider is available"""
        pass
    
    async def warmup(self):
        """Warm up the provider (optional)"""
        pass
