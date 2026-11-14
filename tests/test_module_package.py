import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


class ModulePackageTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)
        modules = []
        for name in ("88XXau.ko", "8188eu.ko", "88x2bu.ko"):
            data = name.encode()
            (self.path / name).write_bytes(data)
            modules.append({"module": name, "sha256": hashlib.sha256(data).hexdigest()})
        (self.path / "kernel-verification.json").write_text(json.dumps({
            "kernel_release": "4.14.336-Nethunter-CDC-KSU-g020784b3a0ae",
            "wireless_modules": modules,
        }))

    def package(self):
        return subprocess.run(
            [sys.executable, str(REPO / "scripts/package_module.py"), str(self.path)],
            capture_output=True, text=True,
        )

    def test_preserves_verified_drivers_and_checksums(self):
        result = self.package()
        self.assertEqual(result.returncode, 0, result.stderr)
        with zipfile.ZipFile(self.path / "Narzo20-CDC-KSU-module.zip") as archive:
            for line in archive.read("SHA256SUMS").decode().splitlines():
                expected, name = line.split()
                self.assertEqual(hashlib.sha256(archive.read(name)).hexdigest(), expected)
            self.assertEqual(archive.read("lib/88XXau.ko"), b"88XXau.ko")
            self.assertIn("skip_mount", archive.namelist())

    def test_rejects_corrupted_driver(self):
        (self.path / "88XXau.ko").write_bytes(b"wrong build")
        result = self.package()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Checksum mismatch", result.stderr)
        self.assertFalse((self.path / "Narzo20-CDC-KSU-module.zip").exists())

    def test_service_leaves_other_kernels_untouched(self):
        binary = self.path / "uname"
        binary.write_text("#!/bin/sh\necho other-kernel\n")
        binary.chmod(0o755)
        result = subprocess.run(
            ["/bin/sh", str(REPO / "module/service.sh")],
            env={"PATH": str(self.path)}, capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout + result.stderr, "")

    def test_restores_usb_after_failure_before_ncm_link(self):
        gadget = self.path / "gadget"
        config = gadget / "configs/b.1"
        config.mkdir(parents=True)
        (gadget / "functions/rndis.gs4").mkdir(parents=True)
        (gadget / "functions/ncm.narzo").mkdir()
        (gadget / "UDC").write_text("")
        script = """
            . "$GADGET_SCRIPT"
            G=$TEST_ROOT/gadget
            C=$G/configs/b.1
            R=$G/functions/rndis.gs4
            N=$G/functions/ncm.narzo
            getprop() { echo rndis,adb; }
            restore_names() { return 0; }
            sleep() { :; }
            restore_gadget
        """
        result = subprocess.run(
            ["/bin/sh"], input=script, capture_output=True, text=True,
            env=dict(os.environ, GADGET_SCRIPT=str(REPO / "module/gadget.sh"),
                     TEST_ROOT=str(self.path)),
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((config / "f1").is_symlink())
        self.assertEqual((config / "f1").resolve(), (gadget / "functions/rndis.gs4").resolve())
        self.assertEqual((gadget / "UDC").read_text().strip(), "musb-hdrc")
        self.assertFalse((gadget / "functions/ncm.narzo").exists())


if __name__ == "__main__":
    unittest.main()
