import unittest
from unittest.mock import Mock

import diagnostico_jogs as jogs
import install


class Fixture:
    def __init__(self):
        self.parts = {
            install.NAME_OFFSET: b'DDJ-REV1\0',
            **{offset - 5: bytes.fromhex('554889e5b83f0000005dc3') for offset in install.PID_OFFSETS},
            **jogs.METHODS,
        }

    def __getitem__(self, key):
        return self.parts.get(key.start, b'')[:key.stop - key.start]


class ExecutableChecks(unittest.TestCase):
    def test_accepts_expected_build_and_rejects_changed_method(self):
        binary = Fixture()
        executable = Mock()
        executable.read_bytes.return_value = binary
        jogs.check_executable(executable)
        binary.parts[0x1118650] = b'\x90' * 10
        with self.assertRaisesRegex(ValueError, 'Metodos dos jogs'):
            jogs.check_executable(executable)

    def test_rejects_wrong_usb_patch(self):
        binary = Fixture()
        binary.parts[install.PID_OFFSETS[0] - 5] = b'\0' * 11
        executable = Mock()
        executable.read_bytes.return_value = binary
        with self.assertRaisesRegex(ValueError, 'USB'):
            jogs.check_executable(executable)


if __name__ == '__main__':
    unittest.main()
