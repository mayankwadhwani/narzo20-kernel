import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from verify_abi import verify_versions


class AbiTests(unittest.TestCase):
    expected = {"module_layout": 0x700D6EB7, "usb_function_register": 0x1E1DBB2B}

    def test_matching_module(self):
        verify_versions(self.expected, {"usb_function_register"}, self.expected)

    def test_rejects_original_unpatched_build(self):
        actual = dict(self.expected, module_layout=0x058D63E9)
        with self.assertRaisesRegex(ValueError, "module_layout"):
            verify_versions(actual, {"usb_function_register"}, self.expected)

    def test_rejects_unversioned_import(self):
        with self.assertRaisesRegex(ValueError, "unversioned"):
            verify_versions(self.expected, {"unexpected_import"}, self.expected)

    def test_rejects_missing_layout(self):
        with self.assertRaisesRegex(ValueError, "module_layout"):
            verify_versions({}, set(), self.expected)

    def test_rejects_unknown_versioned_symbol(self):
        actual = dict(self.expected, unexpected_import=123)
        with self.assertRaisesRegex(ValueError, "unexpected_import"):
            verify_versions(actual, {"unexpected_import"}, self.expected)


if __name__ == "__main__":
    unittest.main()
