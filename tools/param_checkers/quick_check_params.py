#!/usr/bin/env python3
"""
快速检查原始模型的参数 - 列出所有参数
"""
import sys
sys.path.insert(0, '/Users/mylianjie/.openclaw/workspace/projects/sherry-desktop-sprite')

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer, Qt
import live2d.v3 as live2d

app = QApplication(sys.argv)

# 创建最小化窗口
from PyQt6.QtOpenGLWidgets import QOpenGLWidget
from PyQt6.QtCore import QTimer

class QuickCheck(QOpenGLWidget):
    def __init__(self):
        super().__init__()
        self.model = None
        
    def initializeGL(self):
        live2d.glInit()
        live2d.init()
        
        self.model = live2d.LAppModel()
        model_json = "/Users/mylianjie/.openclaw/workspace/live2d-models/hanamaru/奶牛猫花丸_完整版.model3.json"
        
        print(f"\n📂 加载模型: {model_json}")
        self.model.LoadModelJson(model_json)
        
        # 获取所有参数
        param_count = self.model.GetParameterCount()
        print(f"\n📊 总参数数量: {param_count}")
        
        print("\n🔍 搜索 'mask' 或 '水印' 参数:")
        found = False
        for i in range(param_count):
            try:
                param_id = self.model.GetParamIds()[i]
                if 'mask' in str(param_id).lower() or 'water' in str(param_id).lower():
                    value = self.model.GetParameterValue(param_id)
                    print(f"  ✅ {param_id}: {value}")
                    found = True
            except:
                pass
        
        if not found:
            print("  ❌ 未找到 mask 相关参数")
        
        print("\n🔍 搜索 'Open_' 参数 (可能是开关类参数):")
        for i in range(param_count):
            try:
                param_id = self.model.GetParamIds()[i]
                if str(param_id).startswith('Open_'):
                    value = self.model.GetParameterValue(param_id)
                    print(f"  - {param_id}: {value}")
            except:
                pass
        
        print("\n🔍 搜索 'Eye' 参数 (前20个):")
        count = 0
        for i in range(param_count):
            try:
                param_id = self.model.GetParamIds()[i]
                if 'eye' in str(param_id).lower() and count < 20:
                    value = self.model.GetParameterValue(param_id)
                    print(f"  - {param_id}: {value}")
                    count += 1
            except:
                pass
        
        print("\n✅ 检查完成")
        QTimer.singleShot(1000, app.quit)

view = QuickCheck()
view.show()
view.hide()  # 隐藏窗口，只在后台运行

sys.exit(app.exec())
