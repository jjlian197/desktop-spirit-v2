#!/usr/bin/env python3
"""
Logger utility for Sherry Desktop Sprite
"""

import sys
import os
from pathlib import Path
from loguru import logger


def setup_logging():
    """Setup logging configuration"""
    
    # Fix Windows console encoding for Unicode characters (仅在非打包环境下)
    if sys.platform == 'win32' and not hasattr(sys, '_MEIPASS'):
        try:
            # Try to reconfigure stdout/stderr to use UTF-8 with surrogateescape
            if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
                sys.stdout.reconfigure(encoding='utf-8', errors='replace')
            if sys.stderr and hasattr(sys.stderr, 'reconfigure'):
                sys.stderr.reconfigure(encoding='utf-8', errors='replace')
        except (AttributeError, OSError):
            # Python < 3.7 fallback or no console available
            pass
        # Also set environment variable for subprocess
        os.environ['PYTHONIOENCODING'] = 'utf-8'
    
    # Create log directory
    log_dir = Path.home() / '.sherry'
    log_dir.mkdir(exist_ok=True)
    
    log_file = log_dir / 'sprite.log'
    
    # Remove default handler
    logger.remove()
    
    # Add console handler only if stdout is available (非打包或有控制台时)
    if sys.stdout and not hasattr(sys, '_MEIPASS'):
        try:
            logger.add(
                sys.stdout,
                format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
                level="INFO",
                colorize=True
            )
        except (TypeError, OSError):
            # 如果添加 console handler 失败（如打包后无控制台），则跳过
            pass
    
    # Add file handler (始终添加，这是主要的日志输出方式)
    logger.add(
        log_file,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function} - {message}",
        level="DEBUG",
        rotation="10 MB",
        retention="5 days",
        encoding="utf-8"
    )
    
    return logger
