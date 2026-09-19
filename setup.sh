#!/usr/bin/env bash
# ==============================================================================
#  OmniContext AI - System Setup & One-Click Dependency Installer
# ==============================================================================
set -e

echo " [1/3] تثبيت الأدوات اللازمة للينكس..."
if command -v apt-get &> /dev/null; then
    sudo apt-get update -y
    sudo apt-get install -y build-essential cmake git curl libssl-dev pkg-config
elif command -v dnf &> /dev/null; then
    sudo dnf groupinstall -y "Development Tools"
    sudo dnf install -y cmake git curl openssl-devel
elif command -v pacman &> /dev/null; then
    sudo pacman -Syu --noconfirm base-devel cmake git curl openssl
fi

echo " [2/3] فحص وتثبيت مجمّع Rust..."
if ! command -v cargo &> /dev/null; then
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
    source "$HOME/.cargo/env"
else
    echo "Rust مثبت بالفعل: $(cargo --version)"
fi

echo " [3/3] بناء محرك OmniContext AI..."
cargo build --release

echo " تم اكتمال الإعداد بنجاح! يمكنك الآن تشغيل الخادم بالأمر:"
echo "   cargo run --release"
echo "   أو ./run.sh"
