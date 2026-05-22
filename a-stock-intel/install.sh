#!/bin/bash
# A-Stock Intel — 安装脚本
# 将工具文件部署到 Hermes Agent 的 tools/ 目录

set -e

HERMES_HOME="${HERMES_HOME:-$HOME/.hermes/hermes-agent}"
TOOLS_DIR="$HERMES_HOME/tools"

if [ ! -d "$TOOLS_DIR" ]; then
    echo "❌ Hermes Agent tools 目录未找到: $TOOLS_DIR"
    echo "   请先安装 Hermes Agent: curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash"
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cp "$SCRIPT_DIR/a_stock_intel_tool.py" "$TOOLS_DIR/"

echo "✅ 已安装到 $TOOLS_DIR/a_stock_intel_tool.py"
echo ""
echo "下一步:"
echo "  1. pip install numpy akshare requests"
echo "  2. 在 Hermes 会话中输入 /reset"
echo "  3. 即可使用 a_stock_market_regime / a_stock_advice / a_stock_daily_briefing"
