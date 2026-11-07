import plistlib
import unittest

from preparar_diagnostico import ALLOW, debug_entitlements


class DebugEntitlementTests(unittest.TestCase):
    def test_retains_existing_entitlements(self):
        original = {'com.apple.security.device.audio-input': True,
                    'com.apple.security.cs.disable-library-validation': True,
                    'other': 'preserved'}
        expected = dict(original, **{ALLOW: True})
        self.assertEqual(plistlib.loads(debug_entitlements(plistlib.dumps(original))), expected)

    def test_rejects_non_dictionary(self):
        with self.assertRaisesRegex(ValueError, 'Entitlements'):
            debug_entitlements(plistlib.dumps(['invalid']))


if __name__ == '__main__':
    unittest.main()
