/* Offline simulation of the Frida hook's object capture and mixer writes. */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const {createRev1FxCueState} = require('./rev1_fx_cue_state');

const hooks = new Map(), immediate = [], timers = [];
const memory = new Map();
const base = 0x100000000n;
class Pointer {
  constructor(value) { this.value = BigInt(value); }
  add(n) { return new Pointer(this.value + BigInt(n)); }
  equals(other) { return this.value === other.value; }
  isNull() { return this.value === 0n; }
  toUInt32() { return Number(this.value & 0xffffffffn); }
  toInt32() { return this.toUInt32() | 0; }
  toString() { return '0x' + this.value.toString(16); }
  readPointer() { return new Pointer(memory.get(this.value) || 0n); }
  readU8() { return Number(memory.get(this.value) || 0); }
  readU32() { return Number(memory.get(this.value) || 0); }
  readFloat() { return Number(memory.get(this.value) || 0); }
  writeFloat(value) { memory.set(this.value, value); }
  readUtf16String() { return 'DDJ-REV1'; }
}
const ptr = x => x instanceof Pointer ? x : new Pointer(x);
const abs = offset => base + BigInt(offset);
const rbBase = ptr(base);
const fnIds = {midiInGetDevCapsW: 1n, midiOutGetDevCapsW: 2n, midiOutShortMsg: 3n};
const fakeWinmm = {getExportByName: name => ptr(fnIds[name])};
function NativeFunction() { return () => 0; }
const Interceptor = {attach(address, callbacks) {
  const key = address.value;
  hooks.set(key, callbacks);
  return {detach() { hooks.delete(key); }};
}};
const sandbox = {
  Process: {getModuleByName: name => name === 'rekordbox.exe' ? {base: rbBase} : fakeWinmm},
  Interceptor, NativeFunction, Memory: {alloc: () => ptr(0x7000)}, ptr,
  createRev1FxCueState, send() {},
  setImmediate: fn => immediate.push(fn),
  setTimeout: fn => { timers.push(fn); return fn; },
  clearTimeout: fn => { const i = timers.indexOf(fn); if (i >= 0) timers.splice(i, 1); },
};
sandbox.globalThis = sandbox;
vm.runInNewContext(fs.readFileSync('rev1_fx_cue_hook.js', 'utf8'), sandbox);
const runImmediate = () => { while (immediate.length) immediate.shift()(); };
const runTimers = () => { while (timers.length) timers.shift()(); };
const object = ptr(0x8000), mask = ptr(0x9000), outHolder = ptr(0xa000), outHandle = ptr(0xb000);
memory.set(object.value, abs(0x54b5f48));
memory.set(object.add(0x48).value, mask.value);
memory.set(object.add(0x68).value, 1);
memory.set(mask.value, 0);
memory.set(outHolder.value, outHandle.value);

// Capture the verified mixer object once and apply master-only mix.
hooks.get(abs(0x2de7320)).onEnter([object]);
runImmediate(); runTimers();
assert.equal(object.add(0x40).readFloat(), 255);
assert.equal(hooks.has(abs(0x2de7320)), false);

// Register the output handle and simulate a CUE LED update.
hooks.get(abs(0xfbdaa5)).onEnter.call({threadId: 7, context: {rdx: ptr(0), rcx: outHolder}});
hooks.get(abs(0xfbdaab)).onEnter.call({threadId: 7, context: {rax: ptr(0)}});
memory.set(mask.value, 1);
hooks.get(abs(0xfbde1c)).onEnter.call({context: {rcx: outHandle, rdx: ptr(0x7f5490)}});
runTimers();
assert.equal(object.add(0x40).readFloat(), 128);

// Disable master, keep the channel selected: cue-only mix.
memory.set(object.add(0x68).value, 0);
hooks.get(abs(0xfbde1c)).onEnter.call({context: {rcx: outHandle, rdx: ptr(0x006396)}});
runTimers();
assert.equal(object.add(0x40).readFloat(), 0);

// A stale or changed object must not be written, and the finder is rearmed.
memory.set(object.value, 0xdeadn);
hooks.get(abs(0xfbde1c)).onEnter.call({context: {rcx: outHandle, rdx: ptr(0x7f6396)}});
runTimers();
assert.equal(object.add(0x40).readFloat(), 0);
assert.equal(hooks.has(abs(0x2de7320)), true);
console.log('Hook de fone: captura, mistura e protecao contra ponteiro antigo passaram.');
