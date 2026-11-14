import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from verify_kernel import OVERRIDES, read_config, verify_config


class KernelConfigTests(unittest.TestCase):
    def setUp(self):
        self.original = read_config(ROOT / "config/narzo20-nethunter-v2.config")
        self.current = dict(self.original, **OVERRIDES)

    def test_planned_feature_delta(self):
        verify_config(self.original, self.current)

    def test_rejects_lost_nethunter_feature(self):
        self.current["CONFIG_USB_CONFIGFS_F_HID"] = "n"
        with self.assertRaisesRegex(ValueError, "USB_CONFIGFS_F_HID"):
            verify_config(self.original, self.current)

    def test_rejects_force_loading(self):
        self.current["CONFIG_MODULE_FORCE_LOAD"] = "y"
        with self.assertRaisesRegex(ValueError, "MODULE_FORCE_LOAD"):
            verify_config(self.original, self.current)

    def test_rejects_lost_root(self):
        self.current["CONFIG_KSU"] = "n"
        with self.assertRaisesRegex(ValueError, "CONFIG_KSU"):
            verify_config(self.original, self.current)

    def test_rejects_unplanned_new_feature(self):
        self.current["CONFIG_UNREVIEWED_FEATURE"] = "y"
        with self.assertRaisesRegex(ValueError, "UNREVIEWED_FEATURE"):
            verify_config(self.original, self.current)


if __name__ == "__main__":
    unittest.main()
