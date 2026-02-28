#!/usr/bin/env python3
"""
Logger utility for Sherry Desktop Sprite
"""

import sys
from pathlib import Path
from loguru import logger


def setup_logging():
    """Setup logging configuration"""
    
    # Create log directory
    log_dir = Path.home() / '.sherry'
    log_dir.mkdir(exist_ok=True)
    
    log_file = log_dir / 'sprite.log'
    
    # Remove default handler
    logger.remove()
    
    # Add console handler
    logger.add(
        sys.stdout,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
        level="INFO",
        colorize=True
    )
    
    # Add file handler
    logger.add(
        log_file,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function} - {message}",
        level="DEBUG",
        rotation="10 MB",
        retention="5 days",
        encoding="utf-8"
    )
    
    return logger
