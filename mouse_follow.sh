#!/bin/bash
# Sherry Desktop Sprite - 鼠标跟随启动脚本

cd "$(dirname "$0")"

echo "🐱 启动雪莉鼠标跟随系统..."
echo ""

# 激活虚拟环境
source venv/bin/activate

# 检查依赖
pip show pynput &> /dev/null || pip install pynput -q
pip show websockets &> /dev/null || pip install websockets -q

echo "✅ 依赖检查完成"
echo "🎯 模式: 自然模式 (头部50%, 眼神100%)"
echo "🛑 按 Ctrl+C 停止"
echo ""

# 启动跟随
python3 mouse_tracker.py
