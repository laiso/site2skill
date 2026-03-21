#!/usr/bin/env python3
"""Build script to compile Rust binary and create Python wheels."""

import os
import shutil
import subprocess
import sys
from pathlib import Path


def get_platform_tag():
    """Get the platform tag for the current system."""
    import sysconfig

    # Get platform tag from sysconfig
    platform = sysconfig.get_platform()
    if sys.platform == "darwin":
        # macOS
        arch = platform.split("-")[-1]  # arm64 or x86_64
        # Get macOS version
        import platform as plat
        mac_version = plat.mac_ver()[0]
        major_version = int(mac_version.split(".")[0])
        if major_version >= 11:
            return f"macosx_{major_version}_0_{arch}"
        else:
            return f"macosx_10_9_{arch}"
    elif sys.platform == "linux":
        # Linux
        arch = platform.split("-")[-1]
        # Check for musl vs glibc
        try:
            ldd_output = subprocess.check_output(["ldd", "--version"], text=True)
            if "musl" in ldd_output:
                return f"musllinux_1_2_{arch}"
            else:
                return f"manylinux_2_17_{arch}"
        except Exception:
            return f"manylinux_2_17_{arch}"
    elif sys.platform == "win32":
        arch = "win_amd64" if platform.endswith("AMD64") else "win_arm64"
        return arch
    else:
        raise RuntimeError(f"Unsupported platform: {sys.platform}")


def build_rust_binary(target_dir: Path):
    """Build the Rust binary in release mode."""
    print("Building Rust binary...")

    # Determine target triple
    if sys.platform == "darwin":
        import platform as plat
        arch = plat.machine()
        if arch == "arm64":
            target = "aarch64-apple-darwin"
        else:
            target = "x86_64-apple-darwin"
    elif sys.platform == "linux":
        import platform as plat
        arch = plat.machine()
        if arch == "aarch64":
            target = "aarch64-unknown-linux-gnu"
        else:
            target = "x86_64-unknown-linux-gnu"
    elif sys.platform == "win32":
        target = "x86_64-pc-windows-msvc"
    else:
        raise RuntimeError(f"Unsupported platform: {sys.platform}")

    # Build command
    cmd = [
        "cargo",
        "build",
        "--release",
        "--target",
        target,
        "--manifest-path",
        "Cargo.toml",
    ]

    # Set environment variables for memory-efficient build
    env = os.environ.copy()
    env["CARGO_INCREMENTAL"] = "0"
    env["CARGO_BUILD_JOBS"] = "1"

    result = subprocess.run(cmd, env=env, cwd=Path(__file__).parent.parent)

    if result.returncode != 0:
        print("Error: Rust build failed", file=sys.stderr)
        sys.exit(1)

    # Copy binary to target directory
    if sys.platform == "win32":
        binary_name = "site2skill.exe"
    else:
        binary_name = "site2skill"

    target_path = Path(__file__).parent.parent / "target" / target / "release" / binary_name
    dest_path = target_dir / "bin" / binary_name

    dest_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(target_path, dest_path)
    print(f"Copied binary to {dest_path}")


def main():
    """Main build function."""
    # Get the python package directory
    package_dir = Path(__file__).parent / "python" / "site2skill"

    # Build Rust binary
    build_rust_binary(package_dir)

    print("Build complete!")


if __name__ == "__main__":
    main()
