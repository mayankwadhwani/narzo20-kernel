#!/usr/bin/env python3
"""Verify the kernel feature delta and each bundled driver's ABI."""
import gzip
import hashlib
import json
import os
import shutil
from pathlib import Path

from verify_abi import output, verify_versions

OVERRIDES = {
    "CONFIG_LOCALVERSION": '"-Nethunter-CDC-KSU"',
    "CONFIG_88XXAU": "m",
    "CONFIG_RTL8188EU": "m",
    "CONFIG_RTL8822BU": "m",
    "CONFIG_USB_CONFIGFS_NCM": "y",
    "CONFIG_USB_CONFIGFS_ECM": "y",
    "CONFIG_USB_F_NCM": "y",
    "CONFIG_USB_F_ECM": "y",
}


def read_config(path):
    result = {}
    for line in Path(path).read_text().splitlines():
        if line.startswith("CONFIG_") and "=" in line:
            key, value = line.split("=", 1)
            result[key] = value
        elif line.startswith("# CONFIG_") and line.endswith(" is not set"):
            result[line[2:-11]] = "n"
    return result


def verify_config(original, current):
    expected = dict(original, **OVERRIDES)
    changed = {
        key: (expected.get(key, "n"), current.get(key, "n"))
        for key in expected.keys() | current.keys()
        if expected.get(key, "n") != current.get(key, "n")
    }
    if changed:
        raise ValueError(f"Unplanned kernel configuration changes: {changed}")
    for key in ("CONFIG_KSU", "CONFIG_KSU_MANUAL_HOOK", "CONFIG_MODVERSIONS"):
        if current.get(key) != "y":
            raise ValueError(f"Required option missing: {key}")
    if current.get("CONFIG_MODULE_FORCE_LOAD", "n") != "n":
        raise ValueError("Forced module loading must remain disabled")


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    repo = Path(__file__).resolve().parents[1]
    build = Path(os.environ.get("BUILD_DIR", repo / ".build")).resolve()
    out = build / "out"
    artifacts = Path(os.environ.get("ARTIFACT_DIR", repo / "artifacts")).resolve()
    verify_config(read_config(repo / "config/narzo20-nethunter-v2.config"),
                  read_config(out / ".config"))
    release = (out / "include/config/kernel.release").read_text().strip()
    if release != "4.14.336-Nethunter-CDC-KSU-g020784b3a0ae":
        raise ValueError(f"Unexpected kernel release: {release}")
    image = gzip.decompress((out / "arch/arm64/boot/Image.gz").read_bytes())
    if image[56:60] != b"ARMd" or release.encode() not in image:
        raise ValueError("Invalid ARM64 kernel image")
    if b"loading out-of-tree module taints kernel" not in image:
        raise ValueError("Normal module loader path is absent from the image")
    symbols = {}
    for line in (out / "Module.symvers").read_text().splitlines():
        crc, name, *_ = line.split()
        symbols[name] = int(crc, 16)
    drivers = json.loads((repo / "sources/wireless.json").read_text())
    verified = []
    paths = []
    for driver in drivers:
        matches = list(out.rglob(driver["module_name"] + ".ko"))
        if len(matches) != 1:
            raise ValueError(f"Expected one module for {driver['name']}: {matches}")
        module = matches[0]
        versions = {
            name: int(crc, 16)
            for crc, name in (line.split() for line in
                             output("modprobe", "--dump-modversions", str(module)).splitlines())
        }
        undefined = {
            line.split()[-1] for line in
            output("llvm-nm", "--undefined-only", str(module)).splitlines()
        }
        verify_versions(versions, undefined, symbols)
        magic = output("modinfo", "-F", "vermagic", str(module))
        expected_magic = release + " SMP preempt mod_unload modversions aarch64"
        if magic != expected_magic or output("modinfo", "-F", "version", str(module)) != driver["version"]:
            raise ValueError(f"Driver identity mismatch: {module.name}")
        verified.append({
            "module": module.name, "version": driver["version"],
            "sha256": digest(module), "verified_symbol_versions": len(versions),
        })
        paths.append(module)
    artifacts.mkdir(parents=True, exist_ok=True)
    allowed_files = {p.name for p in paths} | {
        "Image.gz", "kernel.config", "Module.symvers", "kernel-verification.json",
        "LICENSE", "README.txt", "wireless-sources.json", "SHA256SUMS",
        "Narzo20-CDC-KSU-module.zip",
    }
    unexpected = {p.name for p in artifacts.iterdir()} - allowed_files
    if unexpected:
        raise ValueError(f"Use an empty artifact directory when changing target: {unexpected}")
    for source in paths + [out / "arch/arm64/boot/Image.gz", out / ".config", out / "Module.symvers"]:
        shutil.copyfile(source, artifacts / ("kernel.config" if source.name == ".config" else source.name))
    manifest = {
        "kernel_release": release,
        "kernel_image_sha256": hashlib.sha256(image).hexdigest(),
        "kernel_gzip_sha256": digest(out / "arch/arm64/boot/Image.gz"),
        "ksu_commit": "fc33995cedc5e0ebf719745c71fe15e78694260f",
        "ksu_version": 33132,
        "wireless_modules": verified,
        "runtime_tested": False,
    }
    (artifacts / "kernel-verification.json").write_text(json.dumps(manifest, indent=2) + "\n")
    shutil.copyfile(repo / "LICENSE", artifacts / "LICENSE")
    shutil.copyfile(repo / "docs/kernel-artifact-notes.txt", artifacts / "README.txt")
    shutil.copyfile(repo / "sources/wireless.json", artifacts / "wireless-sources.json")
    files = sorted(p for p in artifacts.iterdir() if p.is_file() and p.name != "SHA256SUMS")
    (artifacts / "SHA256SUMS").write_text(
        "".join(f"{digest(p)}  {p.name}\n" for p in files))
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
