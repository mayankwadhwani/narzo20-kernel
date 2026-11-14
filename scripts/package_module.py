#!/usr/bin/env python3
"""Package verified kernel artifacts as a script-only KernelSU module."""
import hashlib
import json
import sys
import zipfile
from pathlib import Path

repo = Path(__file__).resolve().parents[1]
artifacts = Path(sys.argv[1] if len(sys.argv) > 1 else repo / "artifacts")
manifest = json.loads((artifacts / "kernel-verification.json").read_text())
if manifest["kernel_release"] != "4.14.336-Nethunter-CDC-KSU-g020784b3a0ae":
    raise ValueError("Wrong kernel artifact")
files = {p.name: p.read_bytes() for p in (repo / "module").iterdir() if p.is_file()}
files["LICENSE"] = (repo / "LICENSE").read_bytes()
expected = {"88XXau.ko", "8188eu.ko", "88x2bu.ko"}
if {m["module"] for m in manifest["wireless_modules"]} != expected:
    raise ValueError("Missing or unexpected wireless driver")
for module in manifest["wireless_modules"]:
    data = (artifacts / module["module"]).read_bytes()
    if hashlib.sha256(data).hexdigest() != module["sha256"]:
        raise ValueError(f"Checksum mismatch: {module['module']}")
    files["lib/" + module["module"]] = data
files["SHA256SUMS"] = "".join(
    f"{hashlib.sha256(data).hexdigest()}  {name}\n"
    for name, data in sorted(files.items())
).encode()
output = artifacts / "Narzo20-CDC-KSU-module.zip"
with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
    for name, data in sorted(files.items()):
        entry = zipfile.ZipInfo(name, (2026, 1, 1, 0, 0, 0))
        entry.compress_type = zipfile.ZIP_DEFLATED
        entry.external_attr = (0o100755 if name.endswith(".sh") else 0o100644) << 16
        archive.writestr(entry, data)
with zipfile.ZipFile(output) as archive:
    if archive.testzip() is not None or set(archive.namelist()) != set(files):
        raise ValueError("Module archive verification failed")
(artifacts / "SHA256SUMS").write_text("".join(
    f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}\n"
    for p in sorted(artifacts.iterdir())
    if p.is_file() and p.name != "SHA256SUMS"
))
print(f"{hashlib.sha256(output.read_bytes()).hexdigest()}  {output}")
