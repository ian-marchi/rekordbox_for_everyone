/* Logica portavel; ainda requer adaptador MIDI do macOS e teste com hardware. */
(function (root) {
  'use strict';
  function createMacFxProfile(createState) {
    const state = createState();
    function process(status, control, value) {
      const fxSide = status === 0x94 || status === 0x95;
      const fxControl = control === 0x50 || control === 0x06 || control === 0x07 ||
                        (control >= 0x70 && control <= 0x72);
      if (!fxSide || !fxControl) return {handled: false, input: [], output: []};
      return state.process(status, control, value);
    }
    function stemLed(status, control, value) {
      if (![0x97, 0x99, 0x9b, 0x9d].includes(status) || control < 0x30 || control > 0x32)
        return null;
      return value === 0 ? 0x7f : 0;
    }
    return {process, flushFx: state.flushFx, armedLed: state.armedLed, stemLed};
  }
  root.createMacFxProfile = createMacFxProfile;
  if (typeof module !== 'undefined' && module.exports) module.exports = {createMacFxProfile};
})(globalThis);
