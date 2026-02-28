#!/usr/bin/env python3
"""
详细检查原始模型的所有参数
"""
import sys
sys.path.insert(0, '/Users/mylianjie/.openclaw/workspace/projects/sherry-desktop-sprite')

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer
from PyQt6.QtOpenGLWidgets import QOpenGLWidget
import live2d.v3 as live2d

app = QApplication(sys.argv)

class DetailCheck(QOpenGLWidget):
    def __init__(self):
        super().__init__()
        self.model = None
        
    def initializeGL(self):
        live2d.glInit()
        live2d.init()
        
        self.model = live2d.LAppModel()
        model_json = "/Users/mylianjie/.openclaw/workspace/live2d-models/hanamaru/奶牛猫花丸_完整版.model3.json"
        
        print(f"加载模型: {model_json}")
        self.model.LoadModelJson(model_json)
        
        # 获取所有参数 ID
        print("\n📊 正在获取所有参数...")
        param_ids = self.model.GetParamIds()
        print(f"参数数量: {len(param_ids)}")
        
        # 查找 Open_EyeMask4
        print("\n🔍 查找 Open_EyeMask4:")
        if "Open_EyeMask4" in param_ids:
            print("  ✅ 找到 Open_EyeMask4!")
            value = self.model.GetParameterValue("Open_EyeMask4")
            print(f"  当前值: {value}")
        else:
            print("  ❌ 未找到 Open_EyeMask4")
        
        # 打印所有包含 'Eye' 的参数
        print("\n🔍 所有包含 'Eye' 的参数:")
        for pid in param_ids:
            if 'eye' in pid.lower():
                try:
                    value = self.model.GetParameterValue(pid)
                    print(f"  - {pid}: {value}")
                except Exception as e:
                    print(f"  - {pid}: (error: {e})")
        
        # 打印所有参数（保存到文件）
        print("\n📝 保存所有参数到 params.txt...")
        with open('/Users/mylianjie/.openclaw/workspace/projects/sherry-desktop-sprite/all_params.txt', 'w') as f:
            for pid in sorted(param_ids):
                try:
                    value = self.model.GetParameterValue(pid)
                    f.write(f"{pid}: {value}\n")
                except:
                    f.write(f"{pid}: ERROR\n")
        print("  ✅ 已保存")
        
        QTimer.singleShot(500, app.quit)

view = DetailCheck()
view.show()
view.hide()

sys.exit(app.exec())
