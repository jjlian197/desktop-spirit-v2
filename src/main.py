#!/usr/bin/env python3
"""
Sherry Desktop Sprite - Entry Point
🐱💜 A cute desktop pet powered by Live2D and PyQt6
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.app import main

if __name__ == '__main__':
    sys.exit(main())
