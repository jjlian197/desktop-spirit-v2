#!/bin/bash
#
# Sherry Desktop Sprite - 启动脚本 🐱💜
# 一键启动雪莉桌面精灵
#
# 用法:
#   ./start_sherry.sh         # 交互模式（显示终端）
#   ./start_sherry.sh silent  # 静默模式（后台运行，不显示终端）
#   ./start_sherry.sh stop    # 停止雪莉
#

# 获取项目目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$SCRIPT_DIR"
VENV_PATH="$PROJECT_DIR/venv"

# 进程 PID 文件
MAIN_PID_FILE="/tmp/sherry_main.pid"
BRAIN_PID_FILE="/tmp/sherry_brain.pid"

# 日志文件
MAIN_LOG="$PROJECT_DIR/sprite_main.log"
BRAIN_LOG="$PROJECT_DIR/sprite_brain.log"

# 检查是否为静默模式
SILENT_MODE=false
if [ "$1" = "silent" ] || [ "$1" = "-s" ] || [ "$1" = "--silent" ]; then
    SILENT_MODE=true
fi

# 停止雪莉
if [ "$1" = "stop" ] || [ "$1" = "--stop" ]; then
    echo "🛑 正在关闭雪莉..."
    if [ -f "$MAIN_PID_FILE" ]; then
        kill $(cat "$MAIN_PID_FILE") 2>/dev/null || true
        rm -f "$MAIN_PID_FILE"
    fi
    if [ -f "$BRAIN_PID_FILE" ]; then
        kill $(cat "$BRAIN_PID_FILE") 2>/dev/null || true
        rm -f "$BRAIN_PID_FILE"
    fi
    echo "✅ 雪莉已关闭"
    exit 0
fi

# 检查虚拟环境
if [ ! -d "$VENV_PATH" ]; then
    echo "❌ 未找到虚拟环境: $VENV_PATH"
    echo "请创建虚拟环境并安装依赖:"
    echo "  python3 -m venv venv"
    echo "  source venv/bin/activate"
    echo "  pip install -r requirements.txt"
    exit 1
fi

# 检查端口占用
check_port() {
    local port=$1
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        echo "⚠️  端口 $port 已被占用，可能是雪莉已经在运行"
        return 1
    fi
    return 0
}

if ! check_port 8765 || ! check_port 8766; then
    echo "如需重启，请先运行: $0 stop"
    exit 1
fi

# 激活虚拟环境
source "$VENV_PATH/bin/activate"

# 清理旧 PID 文件
rm -f "$MAIN_PID_FILE" "$BRAIN_PID_FILE"

if [ "$SILENT_MODE" = true ]; then
    # 静默模式 - 后台运行，不显示终端
    echo "🐱 雪莉正在后台启动..."
    
    cd "$PROJECT_DIR"
    
    # 启动主程序
    export PYTHONPATH="$PROJECT_DIR:$PYTHONPATH"
    nohup "$VENV_PATH/bin/python" -m src.main > "$MAIN_LOG" 2>&1 &
    echo $! > "$MAIN_PID_FILE"
    
    # 等待 WebSocket 服务就绪（最多20秒）
    echo "   等待主程序启动..."
    retries=0
    while ! nc -z localhost 8765 2>/dev/null; do
        sleep 0.5
        retries=$((retries + 1))
        if [ $retries -gt 40 ]; then
            echo "   ✗ 主程序启动超时，查看日志: $MAIN_LOG"
            exit 1
        fi
    done
    
    # 启动大脑
    nohup "$VENV_PATH/bin/python" -m src.brain.sprite_brain > "$BRAIN_LOG" 2>&1 &
    echo $! > "$BRAIN_PID_FILE"
    
    sleep 1
    echo "✅ 雪莉已启动（后台运行）"
    echo "   查看日志: tail -f $MAIN_LOG"
    echo "   停止雪莉: $0 stop"
else
    # 交互模式 - 显示终端（原有逻辑）
    
    # 颜色定义
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    BLUE='\033[0;34m'
    PURPLE='\033[0;35m'
    NC='\033[0m'
    
    # 清理函数
    cleanup() {
        echo ""
        echo -e "${YELLOW}🛑 正在关闭雪莉...${NC}"
        if [ -f "$MAIN_PID_FILE" ]; then
            kill $(cat "$MAIN_PID_FILE") 2>/dev/null || true
            rm -f "$MAIN_PID_FILE"
        fi
        if [ -f "$BRAIN_PID_FILE" ]; then
            kill $(cat "$BRAIN_PID_FILE") 2>/dev/null || true
            rm -f "$BRAIN_PID_FILE"
        fi
        echo -e "${GREEN}✅ 雪莉已安全关闭${NC}"
        exit 0
    }
    
    # 捕获 Ctrl+C
    trap cleanup INT TERM
    
    # 打印欢迎信息
    echo ""
    echo -e "${PURPLE}╔════════════════════════════════════════════════╗${NC}"
    echo -e "${PURPLE}║${NC}                                                ${PURPLE}║${NC}"
    echo -e "${PURPLE}║${NC}     🐱💜 雪莉桌面精灵 (Sherry Sprite) 🐱💜      ${PURPLE}║${NC}"
    echo -e "${PURPLE}║${NC}                                                ${PURPLE}║${NC}"
    echo -e "${PURPLE}╚════════════════════════════════════════════════╝${NC}"
    echo ""
    
    echo -e "${GREEN}✅ 虚拟环境已激活${NC}"
    
    # 启动主程序
    echo -e "${BLUE}🚀 启动精灵本体...${NC}"
    cd "$PROJECT_DIR"
    PYTHONPATH="$PROJECT_DIR:$PYTHONPATH" python -m src.main > "$MAIN_LOG" 2>&1 &
    echo $! > "$MAIN_PID_FILE"
    echo -e "${GREEN}   ✓ 精灵本体 PID: $(cat $MAIN_PID_FILE)${NC}"
    
    # 等待 WebSocket 就绪
    echo -e "${YELLOW}   ⏳ 等待 WebSocket 服务就绪...${NC}"
    retries=0
    while ! nc -z localhost 8765 2>/dev/null; do
        sleep 0.5
        retries=$((retries + 1))
        if [ $retries -gt 20 ]; then
            echo -e "${RED}   ✗ WebSocket 启动超时${NC}"
            cleanup
            exit 1
        fi
    done
    
    # 启动大脑
    echo -e "${BLUE}🧠 启动神经大脑...${NC}"
    PYTHONPATH="$PROJECT_DIR:$PYTHONPATH" python -m src.brain.sprite_brain > "$BRAIN_LOG" 2>&1 &
    echo $! > "$BRAIN_PID_FILE"
    echo -e "${GREEN}   ✓ 神经大脑 PID: $(cat $BRAIN_PID_FILE)${NC}"
    
    # 打印状态
    echo ""
    echo -e "${GREEN}✨ 雪莉已成功启动！${NC}"
    echo ""
    echo -e "${BLUE}📊 服务状态:${NC}"
    echo "   • Live2D 窗口:    运行中"
    echo "   • WebSocket:      ws://127.0.0.1:8765/sprite"
    echo "   • HTTP API:       http://127.0.0.1:8766"
    echo ""
    echo -e "${BLUE}📝 日志文件:${NC}"
    echo "   • $MAIN_LOG"
    echo "   • $BRAIN_LOG"
    echo ""
    echo -e "${YELLOW}💡 提示: 按 Ctrl+C 关闭雪莉${NC}"
    echo ""
    echo -e "${PURPLE}💜 喵~ 主人好！雪莉随时待命！${NC}"
    echo ""
    
    # 等待用户中断
    wait
fi
