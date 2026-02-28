#!/usr/bin/env python3
"""
Live2D 参数设置测试脚本
用于验证 Open_EyeMask4 参数设置是否生效
"""

import sys
import json
from pathlib import Path

# 添加 src 目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QPixmap, QScreen
import live2d.v3 as live2d

from src.core.live2d_view import Live2DView

def test_parameter_setting():
    """测试参数设置"""
    app = QApplication(sys.argv)
    
    # 创建视图
    view = Live2DView()
    view.setFixedSize(400, 600)
    view.show()
    
    # 加载模型
    model_path = Path(__file__).parent / "src" / "assets" / "models" / "hanamaru"
    
    def on_model_loaded():
        if not view.model:
            print("⏳ 等待模型加载...")
            QTimer.singleShot(500, on_model_loaded)
            return
        
        print("✅ 模型已加载")
        
        # 列出 EyeMask 相关参数
        print("\n📋 EyeMask 相关参数:")
        params = view.list_parameters("EyeMask")
        for p in params:
            value = view.get_parameter(p)
            print(f"   - {p}: {value}")
        
        # 设置 Open_EyeMask4 参数
        print("\n🔧 设置 Open_EyeMask4 = -1.0")
        
        # 获取当前值
        before = view.get_parameter("Open_EyeMask4")
        print(f"   设置前: {before}")
        
        # 设置值
        success = view.set_parameter("Open_EyeMask4", -1.0)
        print(f"   设置结果: {'成功' if success else '失败'}")
        
        # 验证
        after = view.get_parameter("Open_EyeMask4")
        print(f"   设置后: {after}")
        
        # 如果值没有变化，可能是参数不存在
        if before == after and before == 0.0:
            print("\n⚠️ 警告: 参数值未变化，可能参数不存在或名称错误")
            print("   可用参数示例:")
            all_params = view.list_parameters()
            for p in all_params[:20]:  # 显示前20个
                print(f"     - {p}")
        
        # 尝试 expression 方式
        print("\n🎭 尝试使用 expression '去水印':")
        view.set_expression("去水印")
        
        # 检查设置后的值
        QTimer.singleShot(500, check_after_expression)
    
    def check_after_expression():
        value = view.get_parameter("Open_EyeMask4")
        print(f"   Expression 设置后 Open_EyeMask4: {value}")
        
        # 再次直接设置
        print("\n🔧 再次直接设置 Open_EyeMask4 = -1.0")
        view.set_parameter("Open_EyeMask4", -1.0)
        
        final = view.get_parameter("Open_EyeMask4")
        print(f"   最终值: {final}")
        
        # 5秒后退出
        print("\n⏳ 5秒后自动退出...")
        QTimer.singleShot(5000, app.quit)
    
    # 开始加载模型
    view.load_model(str(model_path))
    
    # 延迟后开始测试
    QTimer.singleShot(2000, on_model_loaded)
    
    print("🚀 启动测试...")
    return app.exec()

if __name__ == "__main__":
    sys.exit(test_parameter_setting())
