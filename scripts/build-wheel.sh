#!/bin/bash
# Build platform-specific wheel for site2skill

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

# Determine platform
if [[ "$(uname -s)" == "Darwin" ]]; then
    ARCH=$(uname -m)
    if [[ "$ARCH" == "arm64" ]]; then
        PLATFORM_TAG="macosx_11_0_arm64"
        RUST_TARGET="aarch64-apple-darwin"
    else
        PLATFORM_TAG="macosx_10_9_x86_64"
        RUST_TARGET="x86_64-apple-darwin"
    fi
elif [[ "$(uname -s)" == "Linux" ]]; then
    ARCH=$(uname -m)
    if ldd --version 2>&1 | grep -q musl; then
        PLATFORM_TAG="musllinux_1_2_${ARCH}"
    else
        PLATFORM_TAG="manylinux_2_17_${ARCH}"
    fi
    RUST_TARGET="${ARCH}-unknown-linux-gnu"
else
    echo "Unsupported platform"
    exit 1
fi

echo "Building for platform: $PLATFORM_TAG"
echo "Rust target: $RUST_TARGET"

# Build Rust binary
echo "Building Rust binary..."
cargo build --release --target "$RUST_TARGET"

# Copy binary to Python package
mkdir -p python/site2skill/bin
cp "target/${RUST_TARGET}/release/site2skill" python/site2skill/bin/
chmod +x python/site2skill/bin/site2skill

# Build wheel
cd python
python -m build --wheel

# Rename wheel with correct platform tag
cd dist
for wheel in site2skill-*-py3-none-any.whl; do
    if [ -f "$wheel" ]; then
        # Extract version from wheel name
        VERSION=$(echo "$wheel" | sed 's/site2skill-\(.*\)-py3-none-any.whl/\1/')
        NEW_NAME="site2skill-${VERSION}-py3-none-${PLATFORM_TAG}.whl"
        mv "$wheel" "$NEW_NAME"
        echo "Renamed: $wheel -> $NEW_NAME"
    fi
done

echo "Build complete!"
ls -lh *.whl
