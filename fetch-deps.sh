#!/usr/bin/env bash
# ==============================================================================
#  M.A.R.K.E.T AI - Native Binaries & Dependencies Fetcher
# ==============================================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_DIR="$SCRIPT_DIR/bin"

mkdir -p "$BIN_DIR"
cd "$BIN_DIR"

echo "=================================================================="
echo " [M.A.R.K.E.T AI] Fetching / Building Native LLM Inference Binaries..."
echo "=================================================================="

# Check if llama-server already exists
if [ -f "llama-server" ] && [ -x "llama-server" ]; then
    echo " Native llama-server binary is already present and executable."
    exit 0
fi

# Detect OS and architecture
OS="$(uname -s)"
ARCH="$(uname -m)"

echo " Detected System: $OS ($ARCH)"

if command -v cmake &> /dev/null && command -v git &> /dev/null; then
    echo " Building llama.cpp from source (optimized for local CPU architecture)..."
    BUILD_TEMP=$(mktemp -d)
    git clone --depth 1 https://github.com/ggerganov/llama.cpp.git "$BUILD_TEMP/llama.cpp"
    mkdir -p "$BUILD_TEMP/llama.cpp/build"
    cd "$BUILD_TEMP/llama.cpp/build"
    cmake .. -DLLAMA_BUILD_SERVER=ON -DBUILD_SHARED_LIBS=ON
    cmake --build . --config Release -j$(nproc 2>/dev/null || sysctl -n hw.ncpu 2>/dev/null || echo 2)
    
    # Copy compiled server and shared libraries
    cp bin/llama-server "$BIN_DIR/"
    cp bin/libllama.so "$BIN_DIR/" 2>/dev/null || true
    cp bin/libggml*.so "$BIN_DIR/" 2>/dev/null || true
    
    rm -rf "$BUILD_TEMP"
    chmod +x "$BIN_DIR/llama-server"
    echo " Compiled and installed llama-server into $BIN_DIR successfully!"
else
    echo " cmake or git not found. Please install build essentials or use Docker Compose."
fi
