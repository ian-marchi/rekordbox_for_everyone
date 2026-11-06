/* Pure MIDI transformation used for validating the proposed FX/CUE behavior. */
(function (root) {
  'use strict';
  function createRev1FxCueState() {
    const selected = [[false, false, false], [false, false, false]];
    const effective = [[false, false, false], [false, false, false]];
    const fxPressed = [[false, false, false], [false, false, false]];
    const beatPressed = [[false, false], [false, false]];
    const pendingFx = [null, null];
    const fxGeneration = [0, 0];
    const lever = [false, false];
    const cues = [false, false];
    const cuePressed = [false, false];
    let master = false;
    let masterPressed = false;

    function fxUpdate(side) {
      const messages = [];
      for (let slot = 0; slot < 3; slot++) {
        const next = lever[side] && selected[side][slot];
        if (next !== effective[side][slot]) {
          effective[side][slot] = next;
          messages.push([0x94 + side, 0x70 + slot, next ? 0x7f : 0]);
        }
      }
      return messages;
    }

    function headphoneMix() {
      // Preserve the previously working master-only position. Use the center
      // when monitoring a channel; neither position is a measured gain ratio.
      const value = master && !cues.some(Boolean) ? 127 : 64;
      return [[0xb6, 0x0c, value], [0xb6, 0x2c, 0]];
    }

    function engineMixValue(masterEnabled, cueMask) {
      // The 7.2.14 mixer uses a 0..255 CUE-to-MASTER position.
      // 0 = CUE, 128 = center, 255 = MASTER.
      if (!masterEnabled) return 0;
      return (cueMask & 0x0f) !== 0 ? 128 : 255;
    }

    function flushFx(side, generation) {
      const pending = pendingFx[side];
      if (!pending || (generation !== undefined && pending.generation !== generation)) {
        return {handled: true, input: [], output: []};
      }
      pendingFx[side] = null;
      const slots = Array.from(pending.slots);
      const active = selected[side].filter(Boolean).length;
      const turnOff = slots.length === 1 && active === 1 && selected[side][slots[0]];
      for (let i = 0; i < 3; i++) selected[side][i] = !turnOff && pending.slots.has(i);
      return {
        handled: true,
        input: fxUpdate(side),
        output: selected[side].map((on, slot) => [0x94 + side, 0x70 + slot, on ? 0x7f : 0])
      };
    }

    function process(status, control, value) {
      if ((status === 0x94 || status === 0x95) && (control === 0x06 || control === 0x07)) {
        const side = status - 0x94, direction = control - 0x06;
        const down = value !== 0;
        if (beatPressed[side][direction] === down) return {handled: true, input: [], output: []};
        beatPressed[side][direction] = down;
        const second = direction === 0 ? 0x7a : 0x7c;
        return {handled: true,
                input: [[status, control, value], [status, second, value], [status, second + 1, value]],
                output: []};
      }
      if ((status === 0x94 || status === 0x95) && control >= 0x70 && control <= 0x72) {
        const side = status - 0x94, slot = control - 0x70;
        if (value !== 0) {
          if (fxPressed[side][slot]) return {handled: true, input: [], output: []};
          fxPressed[side][slot] = true;
          const start = pendingFx[side] === null;
          if (start) pendingFx[side] = {generation: ++fxGeneration[side], slots: new Set()};
          for (let i = 0; i < 3; i++) if (fxPressed[side][i]) pendingFx[side].slots.add(i);
          return {handled: true, input: [], output: [],
                  scheduleFx: start ? {side, generation: pendingFx[side].generation} : null};
        }
        fxPressed[side][slot] = false;
        if (pendingFx[side] && !fxPressed[side].some(Boolean)) return flushFx(side);
        return {handled: true, input: [], output: []};
      }
      if ((status === 0x94 || status === 0x95) && control === 0x50) {
        const side = status - 0x94;
        const prior = flushFx(side);
        lever[side] = value !== 0;
        return {handled: true, input: [...prior.input, ...fxUpdate(side)], output: prior.output};
      }
      if (status === 0x96 && control === 0x63) {
        if (value !== 0) {
          if (masterPressed) return {handled: true, input: [], output: []};
          masterPressed = true;
          master = !master;
          return {handled: true, input: [[status, control, value], ...headphoneMix()],
                  output: [[0x96, 0x63, master ? 0x7f : 0]]};
        }
        masterPressed = false;
        return {handled: true, input: [[status, control, 0]], output: []};
      }
      if ((status === 0x90 || status === 0x91) && control === 0x54) {
        const side = status - 0x90;
        if (value !== 0) {
          if (cuePressed[side]) return {handled: true, input: [], output: []};
          cuePressed[side] = true;
          cues[side] = !cues[side];
          return {handled: true, input: [[status, control, value], ...headphoneMix()], output: []};
        }
        cuePressed[side] = false;
        return {handled: false, input: [], output: []};
      }
      return {handled: false, input: [], output: []};
    }

    function observeOutput(status, control, value) {
      if ((status === 0x90 || status === 0x91) && control === 0x54) {
        cues[status - 0x90] = value !== 0;
      }
      if (status === 0x96 && control === 0x63) master = value !== 0;
    }

    function armedLed(status, control) {
      if ((status === 0x94 || status === 0x95) && control >= 0x70 && control <= 0x72) {
        return selected[status - 0x94][control - 0x70] ? 0x7f : 0;
      }
      return null;
    }

    return {process, flushFx, observeOutput, armedLed, engineMixValue};
  }
  root.createRev1FxCueState = createRev1FxCueState;
  if (typeof module !== 'undefined' && module.exports) module.exports = {createRev1FxCueState};
})(globalThis);
