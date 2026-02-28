#!/usr/bin/env python3
"""
Minimal test for Live2D OpenGL initialization on Apple Silicon
"""

import sys
import platform
print(f"Platform: {platform.platform()}")
print(f"Machine: {platform.machine()}")

from PyQt6.QtWidgets import QApplication
from PyQt6.QtOpenGLWidgets import QOpenGLWidget
from PyQt6.QtCore import Qt, QTimer

app = QApplication(sys.argv)

class TestGL(QOpenGLWidget):
    def __init__(self):
        super().__init__()
        self.live2d = None
        self.model = None
        self.frame = 0
        
    def initializeGL(self):
        print("initializeGL called")
        
        # Import live2d here
        import live2d.v3 as live2d
        self.live2d = live2d
        
        # Ensure context is current
        self.makeCurrent()
        
        print("Calling live2d.init()...")
        live2d.init()
        print("✅ live2d.init() succeeded")
        
        # Schedule model load for next frame (ensure GL fully ready)
        QTimer.singleShot(100, self.load_model)
    
    def load_model(self):
        print("Loading model...")
        self.makeCurrent()
        
        try:
            self.model = self.live2d.LAppModel()
            print("✅ LAppModel created")
            
            model_path = "/Users/mylianjie/.openclaw/workspace/projects/sherry-desktop-sprite/src/assets/models/hanamaru/model.model3.json"
            print(f"Loading from: {model_path}")
            
            self.model.LoadModelJson(model_path)
            print("✅ LoadModelJson succeeded!")
            
            # If we get here, success!
            QTimer.singleShot(500, lambda: app.quit())
            
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
            app.quit()
    
    def paintGL(self):
        self.frame += 1
        if self.model:
            try:
                self.makeCurrent()
                self.model.Update()
                self.model.Draw()
            except Exception as e:
                print(f"paintGL error: {e}")

widget = TestGL()
widget.setMinimumSize(400, 500)
widget.show()

# Timeout after 5 seconds
QTimer.singleShot(5000, app.quit)

print("\nStarting event loop...")
app.exec()

print("\nTest completed")
