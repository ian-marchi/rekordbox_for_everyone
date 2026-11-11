import hashlib
import csv
import io
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

    def test_stems_replace_only_sampler_pad_layer(self):
        original = list(csv.reader(io.StringIO(install.mapping_data().decode('utf-8'))))
        modified = list(csv.reader(io.StringIO(install.mapping_data(stems=True).decode('utf-8'))))
        stem_rows = [row for row in modified if len(row) > 1 and row[1] in
                     {'PAD1_PadMode4', 'PAD2_PadMode4', 'PAD3_PadMode4'}]
        self.assertEqual([(row[0], row[1], row[3], row[8]) for row in stem_rows], [
            ('ActivePartDrums', 'PAD1_PadMode4', '9030', '9030'),
            ('ActivePartVocal', 'PAD2_PadMode4', '9031', '9031'),
            ('ActivePartInst', 'PAD3_PadMode4', '9032', '9032'),
        ])
        preserved = [row for row in original if len(row) < 2 or not (
            row[0].startswith(tuple(f'PAD{i}_Sampler' for i in range(1, 9)))
            and '_PadMode4' in row[1])]
        self.assertEqual([row for row in modified if row not in stem_rows], preserved)

    def test_rejects_incomplete_sampler_mapping(self):
        broken = install.mapping_data().replace(b'PAD8_Sampler,PAD8_PadMode4', b'Changed,PAD8_PadMode4')
        with self.assertRaisesRegex(ValueError, 'sampler'):
            install.stems_mapping(broken)

    def test_windows_map_preserves_snapshot_and_stems_addresses(self):
        data = install.mapping_data(windows_map=True)
        self.assertEqual(data, install.WINDOWS_MAPPING.read_bytes())
        rows = list(csv.reader(io.StringIO(install.mapping_data(stems=True, windows_map=True).decode('utf-8'))))
        stems = [row for row in rows if row and row[0] in
                 {'ActivePartDrums', 'ActivePartVocal', 'ActivePartInst'}]
        self.assertEqual([(row[0], row[4:8]) for row in stems], [
            ('ActivePartDrums', ['9730', '9930', '9B30', '9D30']),
            ('ActivePartVocal', ['9731', '9931', '9B31', '9D31']),
            ('ActivePartInst', ['9732', '9932', '9B32', '9D32']),
        ])


if __name__ == '__main__':
    unittest.main()
