#!/bin/bash
#
# 🎀 Sakiko 模式启动脚本
# 一键启动雪莉，使用 GPT-SoVITS + Sakiko 声音克隆
#

# 使用 zsh 或 bash
if [ -z "$ZSH_VERSION" ]; then
    # 尝试使用 zsh 执行
    if command -v zsh >/dev/null 2>&1; then
        exec zsh "$0" "$@"
    fi
fi

# 颜色定义
PINK='\033[38;5;213m'
PURPLE='\033[38;5;141m'
YELLOW='\033[38;5;227m'
RESET='\033[0m'

echo -e "${PINK}"
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║     🎀 Sakiko Mode - 雪莉桌面精灵 🐱💜                      ║"
echo "║        GPT-SoVITS 声音克隆版                                ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo -e "${RESET}"

# 切换到脚本所在目录
cd "$(dirname "$0")"

# ═══════════════════════════════════════════════════════════════
# 1. 检查并建立 SSH 隧道
# ═══════════════════════════════════════════════════════════════
echo "🔌 检查 SSH 隧道..."

# 检查端口是否已被占用（可能是之前的隧道）
if lsof -Pi :9880 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "   ⚠️ 端口 9880 已被占用，尝试复用现有隧道..."
else
    # 建立 SSH 隧道（后台运行）
    echo "   建立 SSH 隧道: localhost:9880 -> pc:9880"
    ssh -N -L 9880:127.0.0.1:9880 pc &
    SSH_PID=$!
    
    # 等待隧道建立
    sleep 3
    
    # 检查是否成功
    if ! lsof -Pi :9880 -sTCP:LISTEN -t >/dev/null 2>&1; then
        echo -e "${PINK}❌ SSH 隧道建立失败${RESET}"
        echo "   请检查:"
        echo "   1. SSH Config 中是否配置了 'Host pc'"
        echo "   2. 能否正常执行: ssh pc"
        echo "   3. 远程服务器上的 GPT-SoVITS 是否已启动"
        kill $SSH_PID 2>/dev/null
        exit 1
    fi
    
    echo "   ✅ SSH 隧道已建立 (PID: $SSH_PID)"
fi

# ═══════════════════════════════════════════════════════════════
# 2. 配置 GPT-SoVITS 环境变量
# ═══════════════════════════════════════════════════════════════
echo "🎙️ 配置 GPT-SoVITS (Sakiko 声音)..."

# 🚨 必须使用 export，确保子进程能继承
export GPT_SOVITS_URL="http://127.0.0.1:9880/tts"
# 🌐 初始语言：中文（可在菜单栏切换到日语）
export GPT_SOVITS_LANG="zh"

# Sakiko 参考音频配置（Windows 路径，GPT-SoVITS 在 Windows 上运行）
export GPT_SOVITS_REFER_WAV="D:/Workspace/1761703720454-qatfwm-sakiko1-e15/参考/なんだか申し訳ありませんわそれにしても可愛らしいお部屋ですわね.wav"
export GPT_SOVITS_PROMPT_TEXT="なんだか申し訳ありませんわそれにしても可愛らしいお部屋ですわね"
export GPT_SOVITS_PROMPT_LANG="ja"

# 合成参数
export GPT_SOVITS_SPLIT_METHOD="cut5"
export GPT_SOVITS_BATCH_SIZE="1"
export GPT_SOVITS_MEDIA_TYPE="wav"
export GPT_SOVITS_STREAMING="false"
export GPT_SOVITS_SPEED="1.0"

# 采样参数
export GPT_SOVITS_TOP_K="20"
export GPT_SOVITS_TOP_P="0.6"
export GPT_SOVITS_TEMPERATURE="0.6"

# ═══════════════════════════════════════════════════════════════
# 3. 调试：打印环境变量
# ═══════════════════════════════════════════════════════════════
echo ""
echo -e "${YELLOW}📋 环境变量配置:${RESET}"
echo "   GPT_SOVITS_URL=$GPT_SOVITS_URL"
echo "   GPT_SOVITS_REFER_WAV=$GPT_SOVITS_REFER_WAV"
echo "   GPT_SOVITS_PROMPT_TEXT=$GPT_SOVITS_PROMPT_TEXT"
echo ""

# ═══════════════════════════════════════════════════════════════
# 4. 测试 GPT-SoVITS 连接
# ═══════════════════════════════════════════════════════════════
echo "🔍 测试 GPT-SoVITS 连接..."

if curl -s "http://127.0.0.1:9880" >/dev/null 2>&1; then
    echo "   ✅ GPT-SoVITS 服务可访问"
else
    echo -e "${PINK}⚠️ 警告: 无法连接到 GPT-SoVITS${RESET}"
    echo "   请确保远程服务器上的 GPT-SoVITS 已启动:"
    echo "      python api_v2.py"
    read -p "   是否继续启动? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# ═══════════════════════════════════════════════════════════════
# 5. 启动雪莉
# ═══════════════════════════════════════════════════════════════
echo ""
echo -e "${PURPLE}🚀 启动雪莉桌面精灵...${RESET}"
echo ""

# 设置 Python 编码
export PYTHONIOENCODING=utf-8
export PYTHONUNBUFFERED=1

# 🚨 使用 env 确保环境变量传递给 Python
exec python3 -m src.main
