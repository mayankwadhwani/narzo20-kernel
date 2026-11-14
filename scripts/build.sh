#!/usr/bin/env bash
set -euo pipefail

repo_dir="$(cd "$(dirname "$0")/.." && pwd)"
source "$repo_dir/build.env"
build_dir="$(cd "${BUILD_DIR:-$repo_dir/.build}" && pwd)"
artifact_dir="${ARTIFACT_DIR:-$repo_dir/artifacts}"
test ! -e "$artifact_dir/kernel-verification.json" || {
    echo "Use an empty artifact directory when changing build target." >&2
    exit 1
}
export PATH="/usr/lib/llvm-21/bin:$PATH"
clang --version | head -n 1 | grep -F "clang version $CLANG_VERSION"
test -s "$build_dir/out/.config"
test -s "$build_dir/kernel/include/linux/seccomp.h"

cd "$build_dir/kernel"
# This reference kernel supplies symbol versions; it is never a flash artifact.
make O="$build_dir/out" ARCH=arm64 CC=clang LLVM=1 \
    -j"${BUILD_JOBS:-$(getconf _NPROCESSORS_ONLN)}" vmlinux
test -s "$build_dir/out/Module.symvers"

module_dir="$build_dir/cdc-modules"
mkdir -p "$module_dir"
cp drivers/usb/gadget/function/f_ncm.c \
    drivers/usb/gadget/function/f_ecm.c "$module_dir/"
cat > "$module_dir/Makefile" <<'MAKE'
obj-m += usb_f_ncm.o usb_f_ecm.o
usb_f_ncm-y := f_ncm.o
usb_f_ecm-y := f_ecm.o
ccflags-y += -I$(srctree)/drivers/usb/gadget/function
ccflags-y += -I$(srctree)/drivers/usb/gadget
ccflags-y += -I$(srctree)/drivers/usb/gadget/udc
MAKE
make O="$build_dir/out" ARCH=arm64 CC=clang LLVM=1 \
    -j"${BUILD_JOBS:-$(getconf _NPROCESSORS_ONLN)}" M="$module_dir" modules

verification="$build_dir/abi-verification.json"
python3 "$repo_dir/scripts/verify_abi.py" "$repo_dir/abi/nethunter-v2.json" \
    "$module_dir/usb_f_ncm.ko" "$module_dir/usb_f_ecm.ko" > "$verification"
mkdir -p "$artifact_dir"
cp "$module_dir/usb_f_ncm.ko" "$module_dir/usb_f_ecm.ko" "$artifact_dir/"
cp "$verification" "$artifact_dir/abi-verification.json"
cp "$repo_dir/LICENSE" "$artifact_dir/"
cp "$repo_dir/docs/artifact-notes.txt" "$artifact_dir/README.txt"
{
    printf 'Kernel source: %s\n' "$KERNEL_COMMIT"
    printf 'Source archive SHA256: %s\n' "$KERNEL_ARCHIVE_SHA256"
    clang --version
    ld.lld --version
    printf '\nApplied patches:\n'
    sha256sum "$repo_dir/patches/"*.patch
} > "$artifact_dir/build-info.txt"
cd "$artifact_dir"
sha256sum usb_f_ncm.ko usb_f_ecm.ko abi-verification.json \
    build-info.txt LICENSE README.txt > SHA256SUMS
cat abi-verification.json
