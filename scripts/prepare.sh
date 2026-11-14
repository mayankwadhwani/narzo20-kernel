#!/usr/bin/env bash
set -euo pipefail

repo_dir="$(cd "$(dirname "$0")/.." && pwd)"
source "$repo_dir/build.env"
build_dir="${BUILD_DIR:-$repo_dir/.build}"
mkdir -p "$build_dir"
build_dir="$(cd "$build_dir" && pwd)"
test ! -e "$build_dir/kernel" || {
    echo "Source directory already exists; use build.sh to rebuild it." >&2
    exit 1
}

archive="$build_dir/kernel-source.tar.gz"
curl --fail --location --retry 3 \
    "https://codeload.github.com/sarthakroy2002/kernel_realme_RMX2020/tar.gz/$KERNEL_COMMIT" \
    --output "$archive"
printf '%s  %s\n' "$KERNEL_ARCHIVE_SHA256" "$archive" | sha256sum --check
mkdir "$build_dir/kernel" "$build_dir/out"
tar -xzf "$archive" -C "$build_dir/kernel" --strip-components=1

export PATH="/usr/lib/llvm-21/bin:$PATH"
cd "$build_dir/kernel"
git apply --check "$repo_dir/patches/"*.patch
git apply "$repo_dir/patches/"*.patch
printf '%s\n' "-g${KERNEL_COMMIT:0:12}" > .scmversion
cp "$repo_dir/config/narzo20-nethunter-v2.config" "$build_dir/out/.config"
make O="$build_dir/out" ARCH=arm64 CC=clang LLVM=1 olddefconfig
scripts/diffconfig "$repo_dir/config/narzo20-nethunter-v2.config" \
    "$build_dir/out/.config" > "$build_dir/config-delta.txt"
