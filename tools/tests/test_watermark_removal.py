#!/usr/bin/env python3
"""
Live2D 水印移除测试脚本
直接设置 Open_EyeMask4 参数为 -1.0 来隐藏水印
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
    from PyQt6.QtCore import Qt, QTimer
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

# Import after app creation
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
    sys.exit(1)

# Check initialization state and apply watermark removal
def check_and_remove_watermark():
    print("\n📊 State check:")
    print(f"   GL initialized: {view._gl_initialized}")
    print(f"   Live2D initialized: {view._live2d_initialized}")
    print(f"   Model loaded: {view.model is not None}")
    
    if view.model:
        print("\n🎉 Model loaded successfully!")
        
        # 方法 1: 尝试使用 SetExpression
        print("\n📌 方法 1: 尝试使用 SetExpression('去水印')")
        try:
            view.model.SetExpression("去水印")
            print("   ✅ SetExpression 调用成功")
        except Exception as e:
            print(f"   ❌ SetExpression 失败: {e}")
        
        # 等待一下让 expression 生效
        QTimer.singleShot(500, lambda: try_direct_param())
    else:
        print("\n⏳ Model not loaded yet, retrying...")
        QTimer.singleShot(500, check_and_remove_watermark)

def try_direct_param():
    """方法 2: 直接设置参数"""
    print("\n📌 方法 2: 直接设置参数 Open_EyeMask4 = -1.0")
    
    if view.model:
        try:
            # 获取当前参数值
            current_value = view.model.GetParameterValue("Open_EyeMask4")
            print(f"   当前 Open_EyeMask4 值: {current_value}")
            
            # 直接设置参数值
            view.model.SetParameterValue("Open_EyeMask4", -1.0)
            print("   ✅ SetParameterValue 调用成功")
            
            # 验证设置后的值
            new_value = view.model.GetParameterValue("Open_EyeMask4")
            print(f"   设置后 Open_EyeMask4 值: {new_value}")
            
            # 列出所有可用参数，确认参数存在
            param_count = view.model.GetParameterCount()
            print(f"\n   模型共有 {param_count} 个参数")
            
            # 查找类似 EyeMask 的参数
            print("\n   查找 EyeMask 相关参数:")
            for i in range(min(param_count, 200)):  # 只检查前200个
                try:
                    param_id = view.model.GetParamIds()[i] if hasattr(view.model, 'GetParamIds') else f"Param_{i}"
                    if 'mask' in str(param_id).lower() or 'eyemask' in str(param_id).lower():
                        value = view.model.GetParameterValue(param_id)
                        print(f"     - {param_id}: {value}")
                except:
                    pass
                    
        except Exception as e:
            print(f"   ❌ 设置参数失败: {e}")
            import traceback
            traceback.print_exc()
    
    # 截图验证
    QTimer.singleShot(500, take_screenshot)

def take_screenshot():
    """截取屏幕验证效果"""
    print("\n📸 正在截取屏幕...")
    
    try:
        # 截取窗口
        from PyQt6.QtGui import QScreen, QPixmap
        import subprocess
        
        # 使用 macOS screencapture 命令截图
        screenshot_path = Path(__file__).parent / "watermark_test_result.png"
        subprocess.run([
            "screencapture", 
            "-w",  # 截取窗口
            str(screenshot_path)
        ], check=True)
        
        print(f"   ✅ 截图已保存: {screenshot_path}")
        print("\n💡 请检查截图中的水印是否消失")
        print("   如果水印还在，说明需要其他方法")
        
    except Exception as e:
        print(f"   ⚠️ 截图失败: {e}")
    
    # 保持窗口显示
    print("\n⏳ 窗口将保持显示 10 秒...")
    QTimer.singleShot(10000, app.quit)

# Start checking after a short delay
QTimer.singleShot(1000, check_and_remove_watermark)

print("\n⏳ 正在初始化，请稍候...")
exit_code = app.exec()

print("\n" + "=" * 50)
print("测试完成！")
sys.exit(0)
