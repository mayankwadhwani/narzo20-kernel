#!/usr/bin/env python3
"""Add the pinned legacy root driver and Realtek module sources."""
import hashlib
import json
import os
import re
import subprocess
import tarfile
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
BUILD = Path(os.environ.get("BUILD_DIR", REPO / ".build")).resolve()
KERNEL = BUILD / "kernel"
KSU_COMMIT = "fc33995cedc5e0ebf719745c71fe15e78694260f"


def run(*args, cwd=KERNEL):
    return subprocess.check_output(args, cwd=cwd, text=True).strip()


ksu = KERNEL / "KernelSU-Next"
if not ksu.exists():
    run("git", "clone", "--filter=blob:none", "--no-checkout",
        "https://github.com/KernelSU-Next/KernelSU-Next.git", str(ksu))
run("git", "checkout", "--detach", KSU_COMMIT, cwd=ksu)
if (run("git", "rev-parse", "HEAD", cwd=ksu) != KSU_COMMIT
        or run("git", "status", "--porcelain", cwd=ksu)
        or run("git", "rev-list", "--count", "HEAD", cwd=ksu) != "2982"
        or run("git", "describe", "--tags", "--abbrev=0", cwd=ksu) != "v3.2.0-legacy"):
    raise ValueError("KernelSU checkout does not match the pinned legacy build")

link = KERNEL / "drivers/kernelsu"
if not link.exists():
    link.symlink_to("../KernelSU-Next/kernel")
if link.resolve() != ksu / "kernel":
    raise ValueError("Unexpected KernelSU driver symlink")
for relative, entry in [
    ("drivers/Makefile", "obj-$(CONFIG_KSU) += kernelsu/"),
    ("drivers/Kconfig", 'source "drivers/kernelsu/Kconfig"'),
]:
    path = KERNEL / relative
    text = path.read_text()
    if entry not in text:
        path.write_text(text + "\n" + entry + "\n")

downloads = BUILD / "downloads"
downloads.mkdir(exist_ok=True)
drivers = json.loads((REPO / "sources/wireless.json").read_text())
for driver in drivers:
    name, commit = driver["name"], driver["commit"]
    if not re.fullmatch(r"[a-z0-9]+", name) or not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError("Invalid wireless source identifier")
    archive = downloads / (name + ".tar.gz")
    if not archive.exists():
        url = f"https://codeload.github.com/{driver['repository']}/tar.gz/{commit}"
        with urllib.request.urlopen(url, timeout=120) as source, archive.open("wb") as target:
            while chunk := source.read(1024 * 1024):
                target.write(chunk)
    if hashlib.sha256(archive.read_bytes()).hexdigest() != driver["sha256"]:
        raise ValueError(f"Wireless archive checksum mismatch: {name}")
    destination = KERNEL / "drivers/net/wireless/realtek" / name
    if not destination.exists():
        destination.mkdir()
        with tarfile.open(archive) as source:
            members = source.getmembers()
            roots = {Path(m.name).parts[0] for m in members}
            if len(roots) != 1:
                raise ValueError(f"Unexpected archive layout: {name}")
            for member in members:
                parts = Path(member.name).parts
                if (member.name.startswith("/") or ".." in parts
                        or not (member.isfile() or member.isdir())):
                    raise ValueError(f"Unsafe archive member: {member.name}")
                if len(parts) == 1:
                    continue
                target = destination.joinpath(*parts[1:])
                if member.isdir():
                    target.mkdir(parents=True, exist_ok=True)
                else:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(source.extractfile(member).read())
                    target.chmod(member.mode & 0o777)
    parent = destination.parent
    entry = f'source "drivers/net/wireless/realtek/{name}/Kconfig"'
    text = (parent / "Kconfig").read_text()
    if entry not in text:
        anchor = "endif # WLAN_VENDOR_REALTEK"
        if text.count(anchor) != 1:
            raise ValueError("Realtek Kconfig insertion point changed")
        (parent / "Kconfig").write_text(text.replace(anchor, entry + "\n\n" + anchor))
    entry = f"obj-$(CONFIG_{driver['config']}) += {name}/"
    text = (parent / "Makefile").read_text()
    if entry not in text:
        (parent / "Makefile").write_text(text + "\n" + entry + "\n")

for patch in sorted((REPO / "patches/wireless").glob("*.patch")):
    check = subprocess.run(["git", "apply", "--check", str(patch)], cwd=KERNEL,
                           capture_output=True)
    if check.returncode == 0:
        run("git", "apply", str(patch))
    else:
        run("git", "apply", "--reverse", "--check", str(patch))

config = BUILD / "out/.config"
config.write_bytes((REPO / "config/narzo20-nethunter-v2.config").read_bytes())
for symbol in ("KSU", "KSU_MANUAL_HOOK", "USB_CONFIGFS_NCM", "USB_CONFIGFS_ECM"):
    run("scripts/config", "--file", str(config), "--enable", symbol)
for driver in drivers:
    run("scripts/config", "--file", str(config), "--module", driver["config"])
run("scripts/config", "--file", str(config), "--disable", "MODULE_FORCE_LOAD")
run("scripts/config", "--file", str(config), "--set-str",
    "LOCALVERSION", "-Nethunter-CDC-KSU")
print("KernelSU legacy 33132 and the three matching Realtek driver versions are prepared.")
