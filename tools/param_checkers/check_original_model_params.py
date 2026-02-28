#!/usr/bin/env python3
"""
检查原始路径模型的参数列表，找出正确的水印参数名
"""

import sys
from pathlib import Path

# 强制使用原始路径
original_path = Path("/Users/mylianjie/.openclaw/workspace/live2d-models/hanamaru")

print(f"检查模型: {original_path}")
print(f"目录存在: {original_path.exists()}")

if original_path.exists():
    print(f"\n文件列表:")
    for f in original_path.iterdir():
        print(f"  - {f.name}")

sys.path.insert(0, str(Path(__file__).parent))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer

app = QApplication(sys.argv)

from src.core.live2d_view import Live2DView

view = Live2DView()
view.setFixedSize(400, 600)
view.show()

def check_params():
    if not view.model:
        print("⏳ 等待模型加载...")
        QTimer.singleShot(500, check_params)
        return
    
    print("\n✅ 模型已加载")
    print(f"模型路径: {view.model_path}")
    
    # 列出所有参数
    print("\n📋 所有参数列表 (搜索 'mask' 或 'eye'):")
    all_params = view.list_parameters()
    
    mask_params = [p for p in all_params if 'mask' in p.lower() or 'water' in p.lower() or '水印' in p]
    eye_params = [p for p in all_params if 'eye' in p.lower()]
    
    print(f"\n🔍 Mask/水印 相关参数 ({len(mask_params)} 个):")
    for p in mask_params[:20]:
        try:
            value = view.get_parameter(p)
            print(f"  - {p}: {value}")
        except:
            print(f"  - {p}: (error)")
    
    print(f"\n👁️ Eye 相关参数 (前20个):")
    for p in eye_params[:20]:
        try:
            value = view.get_parameter(p)
            print(f"  - {p}: {value}")
        except:
            print(f"  - {p}: (error)")
    
    # 搜索可能的水印参数
    print("\n🔍 其他可能的水印参数:")
    for p in all_params:
        if any(keyword in p.lower() for keyword in ['open', 'show', 'visible', 'display', 'hide']):
            try:
                value = view.get_parameter(p)
                if value != 0:  # 非默认值可能是有意义的参数
                    print(f"  - {p}: {value}")
            except:
                pass
    
    print(f"\n📊 总参数数量: {len(all_params)}")
    
    # 5秒后退出
    QTimer.singleShot(5000, app.quit)

# 加载原始路径模型
view.load_model(str(original_path))
QTimer.singleShot(2000, check_params)

print("🚀 启动检查...")
sys.exit(app.exec())
