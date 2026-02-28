#!/usr/bin/env python3
"""
Test Live2D rendering with proper OpenGL initialization order
This tests the fix for Apple Silicon segmentation fault
"""

import sys
import platform
from pathlib import Path

print(f"Platform: {platform.platform()}")
print(f"Machine: {platform.machine()}")
print("=" * 50)

# Test imports
try:
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtCore import Qt
    print("✅ PyQt6 imported")
except ImportError as e:
    print(f"❌ PyQt6 import failed: {e}")
    sys.exit(1)

try:
    import live2d.v3 as live2d
    print("✅ live2d-py imported")
except ImportError as e:
    print(f"❌ live2d-py import failed: {e}")
    sys.exit(1)

# Create app first
app = QApplication(sys.argv)
print("✅ QApplication created")

# Now test the Live2D view
from src.core.live2d_view import Live2DView, IS_APPLE_SILICON

print(f"Apple Silicon detected: {IS_APPLE_SILICON}")

# Create the OpenGL widget
view = Live2DView()
view.setMinimumSize(400, 500)
view.show()

print("✅ Live2DView created and shown")
print("   OpenGL context will be initialized after show()")

# Try to load model
model_path = Path(__file__).parent / "src" / "assets" / "models" / "hanamaru"
if model_path.exists():
    print(f"📁 Model path found: {model_path}")
    result = view.load_model(str(model_path))
    print(f"   load_model returned: {result}")
else:
    print(f"⚠️  Model path not found: {model_path}")

# Check initialization state after a short delay
def check_state():
    print("\n📊 State check:")
    print(f"   GL initialized: {view._gl_initialized}")
    print(f"   Live2D initialized: {view._live2d_initialized}")
    print(f"   Model loaded: {view.model is not None}")
    print(f"   Pending model: {view._pending_model_path}")
    
    if view.model:
        print("\n🎉 SUCCESS: Model loaded without crash!")
        app.quit()
    else:
        print("\n⏳ Model not loaded yet (may need more time)")
        QTimer.singleShot(1000, check_state)

from PyQt6.QtCore import QTimer
QTimer.singleShot(100, check_state)

# Run for max 10 seconds
QTimer.singleShot(10000, app.quit)

print("\n⏳ Running event loop (max 10 seconds)...")
exit_code = app.exec()

print("\n" + "=" * 50)
if view._live2d_initialized and view.model:
    print("🎉 TEST PASSED: Live2D working correctly!")
    sys.exit(0)
else:
    print("⚠️  TEST INCOMPLETE: Check logs above")
    sys.exit(1)
