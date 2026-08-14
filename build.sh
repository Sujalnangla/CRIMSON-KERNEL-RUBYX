#!/bin/bash
set -e

# --- Environment Configuration ---
export ARCH=arm64
export SUBARCH=arm64

# Adjust this path if your Clang toolchain is located elsewhere
CLANG_DIR="$HOME/android/toolchain/clang/bin"
if [ -d "$CLANG_DIR" ]; then
    export PATH="$CLANG_DIR:$PATH"
fi

# Cross-compilers & Target Triples
export CROSS_COMPILE=aarch64-linux-gnu-
export CROSS_COMPILE_ARM32=arm-linux-gnueabi-

# Directories & Config
OUT_DIR="out"
DEFCONFIG="ruby_defconfig"

echo "=========================================="
echo " Starting Crimson Kernel Build for Ruby   "
echo "=========================================="

# Create output directory if it doesn't exist
mkdir -p $OUT_DIR

# Generate Defconfig if out directory is clean/empty
if [ ! -f "$OUT_DIR/.config" ]; then
    echo "[*] Generating defconfig: $DEFCONFIG"
    make O=$OUT_DIR $DEFCONFIG
fi

# Start Compilation
echo "[*] Compiling kernel with $(nproc) threads..."
make -j$(nproc) O=$OUT_DIR \
    CC=clang \
    LD=ld.lld \
    AR=llvm-ar \
    NM=llvm-nm \
    OBJCOPY=llvm-objcopy \
    OBJDUMP=llvm-objdump \
    STRIP=llvm-strip \
    CLANG_TRIPLE=aarch64-linux-gnu- \
    CROSS_COMPILE=aarch64-linux-gnu- \
    CROSS_COMPILE_ARM32=arm-linux-gnueabi-

echo "=========================================="
echo " Build Completed Successfully!            "
echo " Output images located in: $OUT_DIR/arch/arm64/boot/"
echo "=========================================="
