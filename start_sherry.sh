#!/bin/bash
#
# Sherry Desktop Sprite - 启动脚本 🐱
# 用法:
#   ./start_sherry.sh         # 前台启动（推荐开发）
#   ./start_sherry.sh -b      # 后台启动
#   ./start_sherry.sh stop    # 停止后台进程

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PATH="$SCRIPT_DIR/venv"
PID_FILE="/tmp/sherry.pid"
LOG_FILE="$SCRIPT_DIR/sprite.log"

cd "$SCRIPT_DIR"

# 检查虚拟环境
if [ ! -d "$VENV_PATH" ]; then
    echo "❌ 虚拟环境不存在，请先创建: python3 -m venv venv && pip install -r requirements.txt"
    exit 1
fi

# 停止进程
if [ "$1" = "stop" ]; then
    if [ -f "$PID_FILE" ]; then
        kill $(cat "$PID_FILE") 2>/dev/null && echo "✅ 雪莉已停止"
        rm -f "$PID_FILE"
    else
        echo "ℹ️ 雪莉未在运行"
    fi
    exit 0
fi

# 检查端口
if lsof -Pi :8765 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "⚠️  端口 8765 已被占用，雪莉可能已在运行"
    exit 1
fi

# 激活环境并启动
source "$VENV_PATH/bin/activate"
export PYTHONPATH="$SCRIPT_DIR:$PYTHONPATH"

if [ "$1" = "-b" ] || [ "$1" = "--background" ]; then
    # 后台模式
    nohup python3 -m src.main > "$LOG_FILE" 2>&1 &
    echo $! > "$PID_FILE"
    echo "🐱 雪莉已在后台启动 (PID: $!)"
    echo "   日志: tail -f $LOG_FILE"
    echo "   停止: $0 stop"
else
    # 前台模式（推荐开发使用）
    echo "🐱 启动雪莉...（按 Ctrl+C 停止）"
    python3 -m src.main
fi
