#!/usr/bin/env python3
"""Reject modules with missing or incompatible kernel symbol versions."""
import hashlib
import json
import subprocess
import sys
from pathlib import Path


def verify_versions(actual, undefined, expected):
    if "module_layout" not in actual:
        raise ValueError("module_layout version is missing")
    unversioned = undefined - actual.keys()
    if unversioned:
        raise ValueError(f"unversioned imports: {sorted(unversioned)}")
    mismatches = {
        name: {"module": value, "kernel": expected.get(name)}
        for name, value in actual.items() if expected.get(name) != value
    }
    if mismatches:
        raise ValueError(f"ABI mismatch: {mismatches}")


def output(*args):
    return subprocess.check_output(args, text=True).strip()


def main():
    baseline = json.loads(Path(sys.argv[1]).read_text())
    results = []
    for argument in sys.argv[2:]:
        module = Path(argument)
        versions = {}
        for line in output("modprobe", "--dump-modversions", str(module)).splitlines():
            crc, name = line.split()
            if name in versions:
                raise ValueError(f"duplicate version entry: {name}")
            versions[name] = int(crc, 16)
        undefined = {
            line.split()[-1] for line in
            output("llvm-nm", "--undefined-only", str(module)).splitlines()
        }
        verify_versions(versions, undefined, baseline["crcs"])
        vermagic = output("modinfo", "-F", "vermagic", str(module))
        if vermagic != baseline["vermagic"]:
            raise ValueError(f"vermagic mismatch: {vermagic}")
        alias = output("modinfo", "-F", "alias", str(module))
        if alias != {"usb_f_ncm.ko": "usbfunc:ncm", "usb_f_ecm.ko": "usbfunc:ecm"}[module.name]:
            raise ValueError(f"unexpected module alias: {alias}")
        results.append({
            "module": module.name,
            "sha256": hashlib.sha256(module.read_bytes()).hexdigest(),
            "bytes": module.stat().st_size,
            "verified_symbol_versions": len(versions),
            "vermagic": vermagic,
            "pass": True,
        })
    if len(results) != 2 or len({r["module"] for r in results}) != 2:
        raise ValueError("Both NCM and ECM modules are required")
    print(json.dumps({
        "kernel_image_sha256": baseline["kernel_image_sha256"],
        "modules": results,
        "runtime_tested": False,
    }, indent=2))


if __name__ == "__main__":
    main()
