# Building a complete replacement kernel

The verified Actions target in this repository builds USB gadget modules. A full bootable NetHunter + KernelSU replacement requires additional integration; the reference `vmlinux` must not be flashed.

## Established inputs

Use the archive and hash in `build.env`, the configuration in `config/narzo20-nethunter-v2.config`, and Clang 21.1.8. Keep the Oplus compiler macros from `OplusKernelEnvConfig.mk`: changing them changes shared kernel structures and did not reproduce the installed ABI.

The upstream `build.sh` is not sufficient as-is. It downloads an x86-64 AOSP compiler, fetches an unpinned KernelSU setup script from a `next` branch, and expects external changes absent from the archive.

## KernelSU dependency

The historical legacy dependency can be checked out independently:

```sh
git clone --filter=blob:none --no-checkout \
  https://github.com/KernelSU-Next/KernelSU-Next.git KernelSU-Next
git -C KernelSU-Next checkout --detach fc33995cedc5e0ebf719745c71fe15e78694260f
git -C KernelSU-Next rev-list --count HEAD
git -C KernelSU-Next describe --tags --abbrev=0
```

The last two commands were verified to return `2982` and `v3.2.0-legacy`. Its Kbuild computes `30000 + 2982 + 150 = 33132` and trusts the manager certificate used by the installed 3.2.0 manager.

A full integration must connect `KernelSU-Next/kernel` to `drivers/kernelsu`, add the driver to `drivers/Makefile` and `drivers/Kconfig`, and enable:

```text
CONFIG_KSU=y
CONFIG_KSU_MANUAL_HOOK=y
```

Manual hooks must match this pinned legacy revision. Its Kbuild deliberately errors if the `ksu_handle_sys_reboot` hook is absent. Relevant integration areas include exec handling, access/stat compatibility, Android init read/stat handling, reboot supercalls and input handling. Use the prototypes in this revision's `feature/sucompat.c`, `runtime/ksud_integration.c` and `supercall/supercall.c`.

The current generic manual-hook guide uses some different handler names and options; it is not a drop-in patch for this revision. This repository does not yet contain a reconstructed, boot-tested full manual-hook patch.

The KernelSU Kbuild also changes the source tree during compilation: it adds the `seccomp` field, mount helpers and SELinux compatibility helpers. Those changes must be retained or represented as explicit patches in a reproducible full build.

## External NetHunter drivers

The installed config enables `CONFIG_88XXAU`, `CONFIG_RTL8188EU` and `CONFIG_RTL8822BU`. Their external sources and Kconfig integration are absent from the base archive, and the archive has no `.gitmodules` containing their revisions.

Recover and pin the corresponding release driver sources before claiming a replacement retains all existing NetHunter hardware support. The stock in-tree Realtek driver options are not substitutes for these external additions.

## NCM/ECM and compilation

Once the complete KernelSU and wireless integrations exist, apply the native `cpio` fix and enable:

```text
CONFIG_USB_CONFIGFS_NCM=y
CONFIG_USB_CONFIGFS_ECM=y
```

Kconfig selects the corresponding USB function implementations. Using the existing config as the starting point preserves the established board, filesystem and Android compatibility settings:

```sh
export PATH="/usr/lib/llvm-21/bin:$PATH"
make O=out ARCH=arm64 CC=clang LLVM=1 olddefconfig
make O=out ARCH=arm64 CC=clang LLVM=1 -j4 Image.gz-dtb
```

These are the source tree's build targets, not a claim that the full replacement has been built and boot-tested. Review the resulting config for dropped options, inspect the image, and retain the current ROM ramdisk and correct device DTB when packaging a boot image. Device boot, root, radios and USB runtime tests remain separate from compilation.
