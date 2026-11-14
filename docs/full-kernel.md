# Full kernel build

Select **kernel** in the manual Actions workflow, or run:

```sh
bash scripts/prepare.sh
python3 scripts/prepare_kernel.py
bash scripts/build_kernel.sh
```

The result is `4.14.336-Nethunter-CDC-KSU-g020784b3a0ae`, with NCM/ECM built in. Artifacts contain `Image.gz`, the three wireless modules, the script-only KernelSU module ZIP, kernel configuration, symbol versions, provenance and checksum files. This is not a recovery installer or a complete boot image.

## Kernel loader repair

The base source forced `MODULE_INIT_IGNORE_MODVERSIONS` and `MODULE_INIT_IGNORE_VERMAGIC` on every load, while the configuration disables `CONFIG_MODULE_FORCE_LOAD`. The resulting force-load path returns `-ENOEXEC`. The compiler consequently removes much of the normal loader path.

`module-loader-checks.patch` removes those assignments and changes the bad-CRC return to rejection. Normal checks are restored, and forced loading stays disabled.

## KernelSU

The pinned legacy source is:

```text
KernelSU-Next/KernelSU-Next
fc33995cedc5e0ebf719745c71fe15e78694260f
```

Its Git history has 2,982 commits and tag `v3.2.0-legacy`, giving version `30000 + 2982 + 150 = 33132`. Its manager certificate matches the existing 3.2.0 manager.

`ksu-legacy-manual-hooks.patch` integrates the exact handler interfaces into:

- Exec handling through `do_execveat_common`, retaining kernel-internal file execution behavior.
- Access/stat compatibility and Android 16 init read/stat handling.
- Reboot supercalls, input handling and devpts.

Both `CONFIG_KSU=y` and `CONFIG_KSU_MANUAL_HOOK=y` are required. KernelSU's pinned Kbuild adds its compatibility helpers. Its `seccomp` header backport is also represented explicitly.

## NetHunter wireless drivers

Revisions and archive hashes are pinned in `sources/wireless.json`:

| Module | Source | Vendor version |
| --- | --- | --- |
| `88XXau.ko` | `aircrack-ng/rtl8812au` | `v5.6.4.2_35491.20191025` |
| `8188eu.ko` | `aircrack-ng/rtl8188eus` | `v5.3.9_28540.20180627` |
| `88x2bu.ko` | `cilynx/rtl88x2bu` | `v5.8.7.1_35809.20191129_COEX20191120-7777` |

These vendor versions match the existing kernel. Their original maintainer's exact modified revisions were not available; the replacement uses pinned upstream sources and explicit compatibility patches.

They are built as modules so their private driver symbols do not collide when combined. Install and autoload the matching modules with the new kernel to retain external adapter support. This does not constitute testing with physical adapters.

## Checks and packaging

The verifier rejects configuration changes outside the declared feature delta, lost KernelSU/NetHunter options, force loading, missing or wrong-version drivers, and module ABI mismatches. The compiled image must contain the restored module-loader path.

The native `cpio` fix supports ARM64 and x86-64 Linux builders. Wireless compatibility patches use Kbuild's supported-warning detection and remove an unused, wrongly typed console declaration.

`Image.gz` intentionally omits a replacement DTB. Repack it into the exact current ROM boot image while preserving its ramdisk, header settings and working device DTB. Verify the resulting boot image fits the actual partition and retain a full rollback image before flashing. Compilation and ABI checks remain separate from boot, root and tethering validation.
