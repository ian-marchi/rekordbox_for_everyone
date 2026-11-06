import hashlib
from pathlib import Path
import unittest
from unittest.mock import patch

import install


class BinaryPatchTests(unittest.TestCase):
    def fixture(self):
        original = bytearray(128)
        original[10:19] = b'DDJ-FLX4\0'
        original[30:41] = install.GETTER_PREFIX
        original[60:71] = install.GETTER_PREFIX
        expected = bytearray(original)
        expected[10:18] = b'DDJ-REV1'
        expected[35] = expected[65] = 0x3f
        return bytes(original), bytes(expected)

    def test_only_expected_name_and_pid_bytes_change(self):
        original, expected = self.fixture()
        with patch.multiple(install, NAME_OFFSET=10, PID_OFFSETS=(35, 65),
                            ORIGINAL_SHA256=hashlib.sha256(original).hexdigest(),
                            PATCHED_SHA256=hashlib.sha256(expected).hexdigest()):
            self.assertEqual(install.patch_binary(original), expected)

    def test_mismatched_build_is_rejected(self):
        original, expected = self.fixture()
        with patch.multiple(install, NAME_OFFSET=10, PID_OFFSETS=(35, 65),
                            ORIGINAL_SHA256=hashlib.sha256(original).hexdigest(),
                            PATCHED_SHA256=hashlib.sha256(expected).hexdigest()):
            changed = bytearray(original)
            changed[-1] = 1
            with self.assertRaisesRegex(ValueError, 'SHA-256'):
                install.patch_binary(bytes(changed))

    def test_getter_bytes_checked_even_with_matching_digest(self):
        original, expected = self.fixture()
        changed = bytearray(original)
        changed[35] = 0x44
        with patch.multiple(install, NAME_OFFSET=10, PID_OFFSETS=(35, 65),
                            ORIGINAL_SHA256=hashlib.sha256(changed).hexdigest(),
                            PATCHED_SHA256=hashlib.sha256(expected).hexdigest()):
            with self.assertRaisesRegex(ValueError, 'PID'):
                install.patch_binary(bytes(changed))

    def test_repository_mapping_has_expected_identity(self):
        self.assertTrue(install.mapping_data().startswith(b'@file,1,DDJ-REV1'))


if __name__ == '__main__':
    unittest.main()
