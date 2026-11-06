import unittest

from rev1_fx_cue_launcher import prepare_mapping


def sample():
    result = ['@file,1,DDJ-REV1']
    for side, ch in ((1, '94'), (2, '95')):
        for slot in range(1, 4):
            name = f'FX{side}-{slot}On'
            result.append(f'{name},{name},Button,{ch}{0x6f + slot:02X},,,,,,,,,,,')
        for direction, note in (('Down', '06'), ('Up', '07')):
            name = f'FX{side}-1Beat{direction}'
            result.append(f'{name},{name},Button,{ch}{note},,,,,,,,,,,')
    return ('\r\n'.join(result) + '\r\n').encode()


class MappingTests(unittest.TestCase):
    def test_appends_mix_without_rewriting_existing_map(self):
        raw = sample()
        result, changed = prepare_mapping(raw)
        self.assertTrue(changed)
        self.assertTrue(result.startswith(raw))
        self.assertIn(b'HeadphonesMix,HeadphonesMix,KnobSliderHiRes,B60C', result)
        self.assertIn(b'MasterCue,MasterCue,Button,9663', result)
        for side, ch in ((1, '94'), (2, '95')):
            for slot, direction, code in ((2, 'Down', '7A'), (3, 'Down', '7B'),
                                          (2, 'Up', '7C'), (3, 'Up', '7D')):
                entry = f'FX{side}-{slot}Beat{direction},FX{side}-{slot}Beat{direction},Button,{ch}{code}'
                self.assertIn(entry.encode(), result)
        self.assertEqual(prepare_mapping(result), (result, False))

    def test_rejects_collision(self):
        raw = sample() + b'Other,Other,KnobSlider,B60C,,,,,,,,,,,\r\n'
        with self.assertRaisesRegex(ValueError, 'atribuido'):
            prepare_mapping(raw)

    def test_rejects_missing_effect(self):
        with self.assertRaisesRegex(ValueError, 'FX2-3On'):
            prepare_mapping(sample().replace(b'FX2-3On,FX2-3On', b'Other,Other'))

    def test_appends_master_without_duplicating_existing_mix(self):
        raw = sample() + b'HeadphonesMix,HeadphonesMix,KnobSliderHiRes,B60C,,,,,,,,,,,\r\n'
        result, changed = prepare_mapping(raw)
        self.assertTrue(changed)
        self.assertEqual(result.count(b'HeadphonesMix,HeadphonesMix'), 1)
        self.assertIn(b'MasterCue,MasterCue,Button,9663', result)

    def test_rejects_fx_group_code_collision(self):
        raw = sample() + b'Other,Other,Button,947A,,,,,,,,,,,\r\n'
        with self.assertRaisesRegex(ValueError, '947A'):
            prepare_mapping(raw)

    def test_rejects_missing_original_beat_control(self):
        raw = sample().replace(b'FX2-1BeatUp,FX2-1BeatUp', b'Other,Other')
        with self.assertRaisesRegex(ValueError, 'FX2-1BeatUp'):
            prepare_mapping(raw)


if __name__ == '__main__':
    unittest.main()
