#!/bin/bash
#
# 🎀 Sakiko 模式启动脚本
# 一键启动雪莉，自动检测并启动远程 GPT-SoVITS 服务
#

# 使用 zsh 或 bash
if [ -z "$ZSH_VERSION" ]; then
    if command -v zsh >/dev/null 2>&1; then
        exec zsh "$0" "$@"
    fi
fi

# 颜色定义
PINK='\033[38;5;213m'
PURPLE='\033[38;5;141m'
YELLOW='\033[38;5;227m'
GREEN='\033[38;5;82m'
RESET='\033[0m'

echo -e "${PINK}"
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║     🎀 Sakiko Mode - 雪莉桌面精灵 🐱💜                      ║"
echo "║        GPT-SoVITS 自动启动版                                ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo -e "${RESET}"

# 切换到脚本所在目录
cd "$(dirname "$0")"

# ═══════════════════════════════════════════════════════════════
# 0. 配置参数
# ═══════════════════════════════════════════════════════════════
SSH_HOST="pc"                          # SSH Config 别名
GPT_SOVITS_PORT=9880                   # GPT-SoVITS 端口
# GPT-SoVITS 远程路径配置
GPT_SOVITS_DIR="D:/Workspace/GPT-SoVITS-v2pro-20250604-nvidia50/GPT-SoVITS-v2pro-20250604-nvidia50"
GPT_SOVITS_CONFIG="GPT_SoVITS/configs/tts_infer.yaml"

# ═══════════════════════════════════════════════════════════════
# 1. 检测并启动 GPT-SoVITS 服务（通过 SSH）
# ═══════════════════════════════════════════════════════════════
echo "🔍 检测远程 GPT-SoVITS 服务..."

# 先建立 SSH 隧道（用于检测和后续使用）
if lsof -Pi :$GPT_SOVITS_PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo -e "${GREEN}   ✅ SSH 隧道已存在，复用中${RESET}"
else
    echo "   🔌 建立 SSH 隧道..."
    ssh -N -L $GPT_SOVITS_PORT:127.0.0.1:$GPT_SOVITS_PORT $SSH_HOST &
    SSH_PID=$!
    sleep 3
    
    if ! lsof -Pi :$GPT_SOVITS_PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
        echo -e "${PINK}❌ SSH 隧道建立失败${RESET}"
        kill $SSH_PID 2>/dev/null
        exit 1
    fi
    echo -e "${GREEN}   ✅ SSH 隧道已建立${RESET}"
fi

# 检测 GPT-SoVITS 是否运行
if curl -s "http://127.0.0.1:$GPT_SOVITS_PORT" >/dev/null 2>&1; then
    echo -e "${GREEN}   ✅ GPT-SoVITS 服务已在运行${RESET}"
else
    echo -e "${YELLOW}   ⚠️ GPT-SoVITS 未运行，正在远程启动...${RESET}"
    echo "   📂 工作目录: $GPT_SOVITS_DIR"
    echo "   🚀 启动命令: python api_v2.py -a 127.0.0.1 -p $GPT_SOVITS_PORT"
    
    # 通过 SSH 在远程服务器上启动 GPT-SoVITS（后台运行）
    # 使用 nohup 确保 SSH 断开后服务继续运行
    ssh $SSH_HOST "cd $GPT_SOVITS_DIR && nohup python api_v2.py -a 127.0.0.1 -p $GPT_SOVITS_PORT -c $GPT_SOVITS_CONFIG > gptsovits.log 2>&1 &"
    
    if [ $? -ne 0 ]; then
        echo -e "${PINK}❌ 远程启动 GPT-SoVITS 失败${RESET}"
        echo "   请手动在服务器上启动:"
        echo "      cd $GPT_SOVITS_DIR"
        echo "      python api_v2.py -a 127.0.0.1 -p $GPT_SOVITS_PORT -c $GPT_SOVITS_CONFIG"
        exit 1
    fi
    
    # 等待服务启动
    echo "   ⏳ 等待服务启动..."
    for i in {1..30}; do
        sleep 2
        if curl -s "http://127.0.0.1:$GPT_SOVITS_PORT" >/dev/null 2>&1; then
            echo -e "${GREEN}   ✅ GPT-SoVITS 启动成功！${RESET}"
            break
        fi
        echo "   ... 等待中 ($i/30)"
    done
    
    # 最终检测
    if ! curl -s "http://127.0.0.1:$GPT_SOVITS_PORT" >/dev/null 2>&1; then
        echo -e "${PINK}❌ GPT-SoVITS 启动超时${RESET}"
        echo "   请检查服务器日志: $GPT_SOVITS_DIR/gptsovits.log"
        exit 1
    fi
fi

# ═══════════════════════════════════════════════════════════════
# 2. 配置雪莉环境变量
# ═══════════════════════════════════════════════════════════════
echo ""
echo "🎙️ 配置雪莉 (Sakiko 声音)..."

export GPT_SOVITS_URL="http://127.0.0.1:$GPT_SOVITS_PORT/tts"
export GPT_SOVITS_LANG="zh"  # 默认中文，可在菜单切换

# Sakiko 默认配置
export GPT_SOVITS_REFER_WAV="D:/Workspace/1761703720454-qatfwm-sakiko1-e15/参考/なんだか申し訳ありませんわそれにしても可愛らしいお部屋ですわね.wav"
export GPT_SOVITS_PROMPT_TEXT="なんだか申し訳ありませんわそれにしても可愛らしいお部屋ですわね"
export GPT_SOVITS_PROMPT_LANG="ja"

# 合成参数
export GPT_SOVITS_SPLIT_METHOD="cut5"
export GPT_SOVITS_SPEED="1.0"
export GPT_SOVITS_TOP_K="20"
export GPT_SOVITS_TOP_P="0.6"
export GPT_SOVITS_TEMPERATURE="0.6"

echo -e "${GREEN}   ✅ 配置完成${RESET}"

# ═══════════════════════════════════════════════════════════════
# 3. 启动雪莉
# ═══════════════════════════════════════════════════════════════
echo ""
echo -e "${PURPLE}🚀 启动雪莉桌面精灵...${RESET}"
echo ""

export PYTHONIOENCODING=utf-8
export PYTHONUNBUFFERED=1

python3 -m src.main

# ═══════════════════════════════════════════════════════════════
# 4. 清理（可选：关闭 GPT-SoVITS）
# ═══════════════════════════════════════════════════════════════
echo ""
echo "🛑 雪莉已停止"

# 询问是否关闭远程 GPT-SoVITS（默认不关闭，保持运行）
read -t 5 -p "是否关闭远程 GPT-SoVITS 服务? [y/N] (5秒后默认不关闭): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🔌 正在关闭 GPT-SoVITS..."
    ssh $SSH_HOST "taskkill /F /IM python.exe 2>/dev/null || pkill -f api_v2.py" 2>/dev/null
    echo "   ✅ 已关闭"
else
    echo "💡 GPT-SoVITS 继续在后台运行"
    echo "   如需关闭，请在服务器上执行: taskkill /F /IM python.exe"
fi

echo ""
echo "👋 再见~"
