const assert = require('node:assert/strict');
const {createRev1FxCueState} = require('../windows/rev1_fx_cue_state');
const {createMacFxProfile} = require('./fx_profile');
const profile = createMacFxProfile(createRev1FxCueState);

// A tap arms FX without activating it; the lever gates the chosen effect.
assert.equal(profile.process(0x94, 0x70, 127).handled, true);
assert.deepEqual(profile.process(0x94, 0x70, 0).input, []);
assert.equal(profile.armedLed(0x94, 0x70), 127);
assert.deepEqual(profile.process(0x94, 0x50, 127).input, [[0x94, 0x70, 127]]);
assert.deepEqual(profile.process(0x94, 0x50, 0).input, [[0x94, 0x70, 0]]);
assert.equal(profile.armedLed(0x95, 0x70), 0);

// Other controls, including headphone CUE, are outside this adaptation.
assert.equal(profile.process(0x96, 0x63, 127).handled, false);
for (const status of [0x97, 0x99, 0x9b, 0x9d]) {
  for (const note of [0x30, 0x31, 0x32]) {
    assert.equal(profile.stemLed(status, note, 0), 127);
    assert.equal(profile.stemLed(status, note, 127), 0);
  }
}
assert.equal(profile.stemLed(0x97, 0x33, 0), null);
assert.equal(profile.stemLed(0x94, 0x70, 0), null);
console.log('Logica FX e inversao proposta de LEDs: testes passaram.');
