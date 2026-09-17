#!/usr/bin/env bash
# ==============================================================================
# 🚀 M.A.R.K.E.T. AI Systems - Launch Script
# Modular AI Runtime & Knowledge Extension Toolkit
# ==============================================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=================================================================="
echo "🚀 [M.A.R.K.E.T. AI Core Engine] بدء الفحص والتشغيل التلقائي..."
echo "   Modular AI Runtime & Knowledge Extension Toolkit"
echo "=================================================================="

# 1. المزامنة التلقائية لملفات الإضافات إلى بيئة التشغيل
mkdir -p "$HOME/omnicontext_ai/plugins"
if [ -d "$SCRIPT_DIR/plugins" ]; then
    cp -r "$SCRIPT_DIR/plugins/"* "$HOME/omnicontext_ai/plugins/" 2>/dev/null || true
fi

# 2. التحقق من توفر Rust و Cargo
if ! command -v cargo &> /dev/null; then
    echo "⚠️ بيئة Rust و Cargo غير مثبتة على هذا النظام."
    echo "📥 جاري تثبيت Rust تلقائياً عبر rustup.rs..."
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
    source "$HOME/.cargo/env"
fi

echo "⚙️ بناء وتشغيل المحرك المرن المعتمد على الإضافات..."
echo "📍 لوحة التحكم والمحولات: http://localhost:8080"
echo "──────────────────────────────────────────────────────────────────"

cargo run --release -- "$@"
