"""
PyInstaller runtime hook for macOS app bundle
Fixes OpenGL and Qt environment issues
"""
import os
import sys

def setup_macos_bundle():
    """Setup environment for macOS .app bundle"""
    # Fix Qt platform plugin path
    if hasattr(sys, '_MEIPASS'):
        # Running from PyInstaller bundle
        bundle_dir = sys._MEIPASS
        
        # Set Qt plugin path
        qt_plugin_path = os.path.join(bundle_dir, 'PyQt6', 'Qt6', 'plugins')
        if os.path.exists(qt_plugin_path):
            os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = qt_plugin_path
        
        # Fix OpenGL on macOS
        os.environ['QT_MAC_WANTS_LAYER'] = '1'
        
        # Disable Qt's built-in OpenGL detection (use system)
        os.environ['QT_OPENGL'] = 'desktop'
        
        # Fix for transparent windows
        os.environ['QT_QPA_ENABLE_TERMINAL_KEYBOARD'] = '0'

if sys.platform == 'darwin':
    setup_macos_bundle()
