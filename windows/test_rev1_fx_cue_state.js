const assert = require('node:assert/strict');
const {createRev1FxCueState} = require('./rev1_fx_cue_state');

let state = createRev1FxCueState();
assert.equal(state.engineMixValue(false, 0), 0);
assert.equal(state.engineMixValue(false, 1), 0);
assert.equal(state.engineMixValue(true, 0), 255);
assert.equal(state.engineMixValue(true, 1), 128);
assert.equal(state.engineMixValue(true, 2), 128);
assert.equal(state.engineMixValue(true, 3), 128);
// SHIFT+2 and SHIFT+3 send a single press/release for all three slots on that side.
for (const status of [0x94, 0x95]) {
  for (const [button, extra1, extra2] of [[0x06, 0x7a, 0x7b], [0x07, 0x7c, 0x7d]]) {
    assert.deepEqual(state.process(status, button, 0x7f).input,
      [[status, button, 0x7f], [status, extra1, 0x7f], [status, extra2, 0x7f]]);
    assert.deepEqual(state.process(status, button, 0x7f).input, []);
    assert.deepEqual(state.process(status, button, 0).input,
      [[status, button, 0], [status, extra1, 0], [status, extra2, 0]]);
    assert.deepEqual(state.process(status, button, 0).input, []);
  }
}
assert.equal(state.process(0x96, 0x06, 0x7f).handled, false);
state = createRev1FxCueState();
let event = state.process(0x94, 0x70, 0x7f);
assert.deepEqual(event.input, []);
assert.deepEqual(event.output, []);
const firstTimer = event.scheduleFx;
assert.deepEqual(state.process(0x94, 0x70, 0x7f).output, []);
assert.deepEqual(state.process(0x94, 0x70, 0).output,
  [[0x94, 0x70, 0x7f], [0x94, 0x71, 0], [0x94, 0x72, 0]]);
assert.equal(state.armedLed(0x94, 0x70), 0x7f);

// A stale timer from the first tap must not prematurely flush a later tap.
event = state.process(0x94, 0x71, 0x7f);
assert.deepEqual(state.flushFx(firstTimer.side, firstTimer.generation).output, []);
assert.deepEqual(state.process(0x94, 0x71, 0).output,
  [[0x94, 0x70, 0], [0x94, 0x71, 0x7f], [0x94, 0x72, 0]]);
assert.deepEqual(state.process(0x94, 0x50, 0x7f).input, [[0x94, 0x71, 0x7f]]);

// Overlapping button presses select the group, even if one is released first.
state.process(0x94, 0x70, 0x7f);
state.process(0x94, 0x72, 0x7f);
assert.deepEqual(state.process(0x94, 0x70, 0).input, []);
event = state.process(0x94, 0x72, 0);
assert.deepEqual(event.input, [[0x94, 0x70, 0x7f], [0x94, 0x71, 0], [0x94, 0x72, 0x7f]]);
assert.equal(state.armedLed(0x94, 0x70), 0x7f);
assert.equal(state.armedLed(0x94, 0x71), 0);
assert.equal(state.armedLed(0x94, 0x72), 0x7f);
assert.deepEqual(state.process(0x94, 0x50, 0).input, [[0x94, 0x70, 0], [0x94, 0x72, 0]]);

// A held button and a later press also form a chord after the first timer.
state = createRev1FxCueState();
event = state.process(0x95, 0x70, 0x7f);
state.flushFx(event.scheduleFx.side, event.scheduleFx.generation);
event = state.process(0x95, 0x72, 0x7f);
state.flushFx(event.scheduleFx.side, event.scheduleFx.generation);
assert.equal(state.armedLed(0x95, 0x70), 0x7f);
assert.equal(state.armedLed(0x95, 0x72), 0x7f);
assert.equal(state.armedLed(0x94, 0x70), 0);
assert.deepEqual(state.process(0x95, 0x50, 0x7f).input, [[0x95, 0x70, 0x7f], [0x95, 0x72, 0x7f]]);

// Tapping the one selected effect again switches it off.
state = createRev1FxCueState();
state.process(0x94, 0x72, 0x7f); state.process(0x94, 0x72, 0);
state.process(0x94, 0x72, 0x7f); state.process(0x94, 0x72, 0);
assert.equal(state.armedLed(0x94, 0x72), 0);

// All three held, then the paddle, flushes selection before activation.
state = createRev1FxCueState();
state.process(0x94, 0x70, 0x7f);
state.process(0x94, 0x71, 0x7f);
state.process(0x94, 0x72, 0x7f);
event = state.process(0x94, 0x50, 0x7f);
assert.deepEqual(event.input, [[0x94, 0x70, 0x7f], [0x94, 0x71, 0x7f], [0x94, 0x72, 0x7f]]);
assert.deepEqual(event.output, [[0x94, 0x70, 0x7f], [0x94, 0x71, 0x7f], [0x94, 0x72, 0x7f]]);

state = createRev1FxCueState();
assert.deepEqual(state.process(0x91, 0x54, 0x7f).input,
  [[0x91, 0x54, 0x7f], [0xb6, 0x0c, 64], [0xb6, 0x2c, 0]]);
state = createRev1FxCueState();
event = state.process(0x96, 0x63, 0x7f);
assert.deepEqual(event.input, [[0x96, 0x63, 0x7f], [0xb6, 0x0c, 127], [0xb6, 0x2c, 0]]);
assert.deepEqual(event.output, [[0x96, 0x63, 0x7f]]);
assert.deepEqual(state.process(0x96, 0x63, 0x7f).input, []);
assert.deepEqual(state.process(0x96, 0x63, 0).input, [[0x96, 0x63, 0]]);
assert.deepEqual(state.process(0x90, 0x54, 0x7f).input,
  [[0x90, 0x54, 0x7f], [0xb6, 0x0c, 64], [0xb6, 0x2c, 0]]);
state.process(0x90, 0x54, 0);
state.process(0x91, 0x54, 0x7f);
state.process(0x91, 0x54, 0);
assert.deepEqual(state.process(0x90, 0x54, 0x7f).input.slice(1),
  [[0xb6, 0x0c, 64], [0xb6, 0x2c, 0]]);
assert.deepEqual(state.process(0x91, 0x54, 0x7f).input.slice(1),
  [[0xb6, 0x0c, 127], [0xb6, 0x2c, 0]]);
assert.equal(state.process(0x90, 0x0b, 0x7f).handled, false);
state = createRev1FxCueState();
state.observeOutput(0x91, 0x54, 0x7f);
assert.deepEqual(state.process(0x96, 0x63, 0x7f).input,
  [[0x96, 0x63, 0x7f], [0xb6, 0x0c, 64], [0xb6, 0x2c, 0]]);
state.observeOutput(0x94, 0x72, 0x7f);
assert.equal(state.armedLed(0x94, 0x72), 0);
console.log('FX e CUE: testes da maquina de estados passaram.');
