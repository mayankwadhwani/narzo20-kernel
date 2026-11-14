# Narzo 20 NetHunter CDC + KernelSU builds

The default **kernel** target builds a replacement kernel with NCM/ECM built in, KernelSU-Next legacy 33132, and a corrected module loader. The three external Realtek drivers retain their vendor versions and are packaged as loadable modules.

The old kernel's `load_module()` unconditionally sets both ignore-version flags even though `CONFIG_MODULE_FORCE_LOAD` is disabled. That makes normal insertion fail with `ENOEXEC`. `patches/module-loader-checks.patch` removes those forced flags and restores CRC rejection; it does not enable forced loading.

**The full kernel is experimental; device validation is pending.** `Image.gz` is a kernel component, not a boot image. Preserve the current ROM ramdisk and device DTB when repacking, retain a verified rollback boot image, and install the matching wireless modules.

## Full kernel build

In **Actions → Build Narzo 20 kernel or CDC modules**, select **kernel** and run the workflow. It checks that the only configuration changes are the kernel name, NCM/ECM enablement, and changing the three external wireless drivers from built-ins to modules. KernelSU and the remaining NetHunter options must remain enabled.

Locally, after installing the workflow's Linux dependencies:

```sh
bash scripts/prepare.sh
python3 scripts/prepare_kernel.py
bash scripts/build_kernel.sh
```

See [docs/full-kernel.md](docs/full-kernel.md) for source revisions, integration details and artifact handling.

## Original kernel's USB module target

Builds **NCM and ECM gadget modules** for the Realme Narzo 20 / RMX2193 running:

```text
4.14.336-Nethunter-VoPi-v2-g020784b3a0ae
```

The unified Android 16 ROM identifies the phone as RMX2020. This repository targets the NetHunter VoPi v2 kernel above; it is not a generic RMX2020 kernel installer.

**Status:** the first USB-module Actions build passed, and its binaries match the local builds. Those modules cannot resolve the old kernel's loader defect. The fixed-kernel target above is the repair path.

The modules are intended to add the missing gadget functions while keeping the installed NetHunter and KernelSU kernel. A GitHub Actions run produces `.ko` files, an ABI verification report, build details, licensing information and SHA-256 checksums.

## GitHub Actions

Open **Actions → Build Narzo 20 kernel or CDC modules → Run workflow**, and select **usb-modules**.

The workflow:

1. Uses a pinned Debian container and Clang 21.1.8.
2. Downloads and verifies the exact kernel source archive.
3. Applies the KernelSU compatibility backport and native `cpio` build fix.
4. Builds a reference kernel to generate `Module.symvers`.
5. Builds the standard Linux `usb_f_ncm.ko` and `usb_f_ecm.ko` modules.
6. Rejects missing, unknown or mismatched symbol versions, incorrect vermagic and incorrect module aliases.
7. Uploads artifacts only after those checks pass.

Runs are manual. The workflow has `contents: read` permission, does not need repository secrets, and does not flash a phone. Actions are pinned to commit hashes. The Debian image and source archive are pinned; Debian package revisions can change, so the exact compiler release is checked and compiler details are recorded.

## Build locally on Linux

Install the dependencies listed in `.github/workflows/build.yml`, then run:

```sh
bash scripts/prepare.sh
bash scripts/build.sh
```

`prepare.sh` requires a fresh `.build/kernel` directory. Once preparation has succeeded, `build.sh` can be rerun incrementally. Set `BUILD_JOBS` to control parallelism. `BUILD_DIR` and `ARTIFACT_DIR` override the default `.build` and `artifacts` directories.

On macOS, build inside Linux using Docker/Colima. Keep `BUILD_DIR` on a Linux volume: the kernel source contains filenames that collide on case-insensitive filesystems. For example, after starting Docker:

```sh
mkdir -p artifacts
docker volume create narzo20-kernel-build
docker run --rm \
  -v "$PWD:/repo:ro" \
  -v "$PWD/artifacts:/artifacts" \
  -v narzo20-kernel-build:/build \
  -e BUILD_DIR=/build -e ARTIFACT_DIR=/artifacts \
  -w /repo \
  debian:sid@sha256:e276677157e13bc51ea5b8651f54ad28883f503cc37b3e3af2c4b6cc2f4efe7b \
  bash -c '
    apt-get update &&
    apt-get install -y --no-install-recommends \
      clang-21 llvm-21 lld-21 make gcc g++ bc bison flex \
      libssl-dev libelf-dev python3 git ca-certificates curl \
      xz-utils cpio perl kmod &&
    bash scripts/prepare.sh &&
    bash scripts/build.sh
  '
```

For subsequent builds with that prepared volume, omit `prepare.sh`.

## Source and compatibility evidence

- Kernel base: `sarthakroy2002/kernel_realme_RMX2020`, commit `020784b3a0ae5bdbcb5f7046e7a9874d3918d50a`.
- Archive SHA-256: `7a92fb1fa8f4f56cc6f2560b0fe3e0476608bf70c473625d1a9939037bcaf232`.
- Relevant KernelSU-Next legacy source: `fc33995cedc5e0ebf719745c71fe15e78694260f`. Its Git history reports `v3.2.0-legacy` and 2,982 commits; its version formula yields `33132`, matching the installed driver.
- Target uncompressed kernel SHA-256: `b4c218cdf5f00bd125afce8e78aefc57095e4de5ac6b596fcc174177658bee17`.

The original base archive lacks a change made automatically by KernelSU's `kernel/Kbuild`: adding `atomic_t filter_count` to `struct seccomp` and including `linux/atomic.h`. This affects exported ABI checksums through shared kernel structures.

The running kernel's exported `kheaders.tar.xz` was compared with 5,056 base source headers. After accounting for the exporter's comment removal, that `seccomp` change was the only difference. Applying the upstream backport changed the module ABI check from eight mismatches to all 14 tested exports matching, including `module_layout`.

The module build then matched all **65 NCM** and **43 ECM** version entries against the installed kernel. `abi/nethunter-v2.json` stores the required export CRCs recovered from the published target kernel image. They are used only to check the independently built modules. They are not injected into `Module.symvers` or used to rewrite module metadata.

`patches/native-cpio.patch` replaces the source tree's hardcoded x86-64 `cpio` executable with the native Linux command. This permits the reference build on ARM64 Linux as well as x86-64.

## Scope and remaining device tests

The reference kernel is used to produce symbol versions. It omits KernelSU integration and three external Realtek driver additions that are absent from the base archive. **It is not a replacement boot image and is not uploaded.** The resulting USB modules use the existing kernel, which retains those features.

Build and ABI verification do not prove runtime functionality. Normal NCM insertion was tested from `/data/local/tmp` and a temporary RAM filesystem; both returned `Exec format error`, with no module loaded. The cause is the kernel's contradictory forced-ignore flags and disabled force-loading support. No force flags or metadata rewriting were used by the build or test scripts.

ConfigFS binding with ADB retained, Android tethering, DHCP, Mac traffic, reconnect behavior and reboot persistence remain unverified. Do not force-load these modules or treat the current artifacts as a working tethering fix.

The full-kernel target integrates the missing root hooks and driver sources; its artifacts require separate boot and device validation.

## Tests

```sh
python3 -m unittest discover -s tests -v
```

The rejection tests cover the original incompatible `module_layout` value, missing layout metadata, unversioned imports and symbols absent from the target ABI baseline.

Kernel sources and derived patches are GPL-2.0. See `LICENSE`.
