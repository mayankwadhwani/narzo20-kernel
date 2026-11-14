#!/usr/bin/env bash
set -euo pipefail

repo_dir="$(cd "$(dirname "$0")/.." && pwd)"
source "$repo_dir/build.env"
build_dir="$(cd "${BUILD_DIR:-$repo_dir/.build}" && pwd)"
export PATH="/usr/lib/llvm-21/bin:$PATH"
export KBUILD_BUILD_USER=narzo20
export KBUILD_BUILD_HOST=github-actions
export KBUILD_BUILD_VERSION=1
clang --version | head -n 1 | grep -F "clang version $CLANG_VERSION"

cd "$build_dir/kernel"
make O="$build_dir/out" ARCH=arm64 CC=clang LLVM=1 olddefconfig
scripts/diffconfig "$repo_dir/config/narzo20-nethunter-v2.config" \
    "$build_dir/out/.config" > "$build_dir/config-delta.txt"
make O="$build_dir/out" ARCH=arm64 CC=clang LLVM=1 \
    -j"${BUILD_JOBS:-$(getconf _NPROCESSORS_ONLN)}" Image.gz modules
python3 "$repo_dir/scripts/verify_kernel.py"
python3 "$repo_dir/scripts/package_module.py" "${ARTIFACT_DIR:-$repo_dir/artifacts}"
