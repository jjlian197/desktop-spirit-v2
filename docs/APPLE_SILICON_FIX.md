# Sherry Desktop Sprite - Apple Silicon Fix Summary

## Problem
The Sherry Desktop Sprite was crashing with "Segmentation fault: 11" on Mac mini M4 (Apple Silicon) when trying to render the Hanamaru Live2D model via PyQt6 + live2d-py.

## Root Cause
The Live2D Cubism SDK's OpenGL ES 2.0 renderer requires a specific initialization order when running with an existing OpenGL context (like PyQt6's QOpenGLWidget).

The crash occurred in `CubismOffscreenSurface_OpenGLES2::CreateOffscreenSurface` because:
1. `live2d.init()` was being called BEFORE the OpenGL context was fully ready
2. `live2d.glInit()` was not being called at all - this is required when integrating with an existing OpenGL context
3. Model loading (`LoadModelJson`) was happening before proper OpenGL initialization

## Solution

### 1. Fixed Initialization Order in `live2d_view.py`

**Before (Crash):**
```python
def __init__(self, ...):
    super().__init__(parent)
    live2d.init()  # ❌ Wrong! Called before GL context exists

def initializeGL(self):
    pass  # ❌ glInit() never called
```

**After (Working):**
```python
def initializeGL(self):
    super().initializeGL()
    self.makeCurrent()  # Ensure GL context is current
    live2d.glInit()     # ✅ Initialize OpenGL renderer FIRST
    live2d.init()       # ✅ Then initialize SDK
    # Now safe to load model
```

### 2. Added Deferred Model Loading

Since `initializeGL()` is called asynchronously after the widget is shown, model loading requests made in `__init__()` are now deferred:

```python
def load_model(self, model_path: str) -> bool:
    if not self._gl_initialized or not self._live2d_initialized:
        # Queue for later loading
        self._pending_model_path = model_path
        QTimer.singleShot(100, self._try_load_pending_model)
        return True
```

### 3. Key Changes Made

**File: `src/core/live2d_view.py`**
- Moved `live2d.init()` from `__init__()` to `initializeGL()`
- Added `live2d.glInit()` call BEFORE `live2d.init()`
- Added `self.makeCurrent()` to ensure OpenGL context is active
- Implemented deferred model loading mechanism
- Added Apple Silicon detection and logging

### 4. Also Fixed

**File: `src/core/websocket_server.py`**
- Improved asyncio event loop handling for better stability
- Added proper shutdown handling

## Verification

Run the test to verify the fix:
```bash
cd ~/.openclaw/workspace/projects/sherry-desktop-sprite
source venv/bin/activate
python3 test_live2d.py
```

Expected output:
```
🎉 SUCCESS: Model loaded without crash!
🎉 TEST PASSED: Live2D working correctly!
```

## Running the Application

```bash
cd ~/.openclaw/workspace/projects/sherry-desktop-sprite
source venv/bin/activate
python3 src/main.py
```

The Sherry Desktop Sprite should now:
1. Start without crashing
2. Display the Hanamaru Live2D model
3. Respond to mouse interactions
4. Show expression changes and motions via WebSocket commands

## Known Issues

1. **WebSocket Server**: There may be a "no running event loop" error on Python 3.14 with certain websockets library versions. This doesn't affect the Live2D rendering functionality.

2. **System Tray**: The system tray icon shows a warning "No Icon set" - this is cosmetic and doesn't affect functionality.

3. **High DPI Warning**: A warning about `setHighDpiScaleFactorRoundingPolicy` appears - this is cosmetic.

## Environment

- **Hardware**: Mac mini M4 (Apple Silicon, arm64)
- **OS**: macOS 26.3 (Sequoia)
- **Python**: 3.14.3
- **PyQt6**: 6.4.0+
- **live2d-py**: 0.6.1.1

## References

- Live2D-py GitHub: https://github.com/Arkueid/live2d-py
- Live2D Cubism SDK: https://www.live2d.com/sdk/download/native/
- PyQt6 OpenGL: https://doc.qt.io/qt-6/qopenglwidget.html

---

**Fixed by**:虾老师 (OpenClaw Coder)
**Date**: 2026-02-18
**Status**: ✅ RESOLVED
