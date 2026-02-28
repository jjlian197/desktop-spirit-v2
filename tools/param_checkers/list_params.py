#!/usr/bin/env python3
"""
列出原始模型的所有参数名
"""
import sys
sys.path.insert(0, '/Users/mylianjie/.openclaw/workspace/projects/sherry-desktop-sprite')

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer
from PyQt6.QtOpenGLWidgets import QOpenGLWidget
import live2d.v3 as live2d

app = QApplication(sys.argv)

class ListParams(QOpenGLWidget):
    def __init__(self):
        super().__init__()
        self.model = None
        
    def initializeGL(self):
        try:
            live2d.glInit()
            live2d.init()
            
            self.model = live2d.LAppModel()
            model_json = "/Users/mylianjie/.openclaw/workspace/live2d-models/hanamaru/奶牛猫花丸_完整版.model3.json"
            
            print(f"加载模型...")
            self.model.LoadModelJson(model_json)
            
            # 获取所有参数 ID
            print(f"\n📊 获取参数列表...")
            param_ids = self.model.GetParamIds()
            print(f"总参数数量: {len(param_ids)}\n")
            
            print("🔍 搜索 'Open_' 开头的参数:")
            open_params = [p for p in param_ids if p.startswith('Open_')]
            if open_params:
                for p in open_params:
                    print(f"  - {p}")
            else:
                print("  (无)")
            
            print("\n🔍 搜索 'Mask' 参数:")
            mask_params = [p for p in param_ids if 'Mask' in p]
            if mask_params:
                for p in mask_params:
                    print(f"  - {p}")
            else:
                print("  (无)")
            
            print("\n🔍 搜索 'Eye' 参数 (前30个):")
            eye_params = [p for p in param_ids if 'Eye' in p][:30]
            for p in eye_params:
                print(f"  - {p}")
            
            # 检查是否有水印相关参数
            print("\n🔍 所有参数 (前100个):")
            for p in param_ids[:100]:
                print(f"  {p}")
            
            print(f"\n... 还有 {len(param_ids) - 100} 个参数")
            
        except Exception as e:
            print(f"错误: {e}")
            import traceback
            traceback.print_exc()
        
        QTimer.singleShot(500, app.quit)

view = ListParams()
view.show()
view.hide()

sys.exit(app.exec())
