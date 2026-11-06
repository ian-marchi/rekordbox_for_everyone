const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const base = 0x100000000n, memory = new Map(), hooks = new Map();
const map = 0x200000000n, processorVtable = base + 0x3ae4ae0n;
let next = 0x300000000n, destroyed = [], createdDecks = [], brokenDeck = null;
class P {
  constructor(x) { this.v = BigInt(x instanceof P ? x.v : x); }
  add(n) { return new P(this.v + BigInt(n)); }
  equals(p) { return this.v === p.v; }
  isNull() { return this.v === 0n; }
  readPointer() { return new P(memory.get(this.v) || 0n); }
  writePointer(v) { memory.set(this.v, v.v); }
  readS32() { return Number(memory.get(this.v) || 0); }
  readDouble() { return Number(memory.get(this.v) || 0); }
  toString() { return '0x' + this.v.toString(16); }
}
const ptr = x => new P(x), write = (address, value) => memory.set(BigInt(address), value);
const latencyFn = 0x4444n;
write(processorVtable + 8n, latencyFn);
write(map, base + 0x3adc178n);
write(map + 0x809f8n, 720);
function addProcessor(deck) {
  const p = next; next += 0x50000n;
  const a = p + 0x1000n;
  write(p, processorVtable); write(p + 8n, a); write(p + 0x78n, 3);
  write(a + 0x3ab30n, deck); write(a + 0x3ab38n, 1); write(a + 0x3ab40n, 2.1);
  return p;
}
for (const deck of [1, 2, 3, 4]) {
  const p = deck <= 2 ? addProcessor(deck) : 0n;
  for (const [kind, note, vt] of [[0xb0,0x22,0x3adf120],[0xb0,0x23,0x3adf120],
      [0xb0,0x21,0x3adf120],[0xb0,0x26,0x3adf120],[0x90,0x36,0x3adf4c8],[0x90,0x67,0x3adf4c8]]) {
    const key = ((kind + deck - 1) << 8) | note, data = next; next += 0x200n;
    write(map + 0x140n + BigInt(key * 8), data);
    write(data, base + BigInt(vt)); write(data + 8n, deck); write(data + 0xf8n, p);
  }
}
function NativeFunction(address) {
  if (address.v === base + 0x23c11c0n) return (deck, a, b, kind) => {
    assert.equal(a, 1); assert.equal(b, 2.1); assert.equal(kind, 3);
    createdDecks.push(deck);
    const result = addProcessor(deck);
    if (deck === brokenDeck) write(result + 0x1000n + 0x3ab30n, 99);
    return ptr(result);
  };
  if (address.v === base + 0x23c5a90n) return (p, flag) => { assert.equal(flag, 1); destroyed.push(p.v); return p; };
  if (address.v === latencyFn) return (_p, value) => { assert.equal(value, 720); };
  throw Error('Unexpected native call: ' + address);
}
const sandbox = {Process: {getModuleByName: () => ({base: ptr(base)})}, NativeFunction, ptr,
  Interceptor: {attach(address, handlers) { hooks.set(address.v, handlers); }},
  rpc: {exports: {}}, send() {}};
vm.runInNewContext(fs.readFileSync(process.argv[2], 'utf8'), sandbox);
const result = sandbox.rpc.exports.activate('0x' + map.toString(16));
assert.equal(result.status, 'active'); assert.equal(result.bindings, 12);
assert.deepEqual(createdDecks, [3, 4]);
for (const deck of [3, 4]) {
  const scratch = memory.get(map + 0x140n + BigInt((((0xb0 + deck - 1) << 8) | 0x22) * 8));
  const touch = memory.get(map + 0x140n + BigInt((((0x90 + deck - 1) << 8) | 0x36) * 8));
  assert.notEqual(memory.get(scratch + 0xf8n), 0n);
  assert.equal(memory.get(scratch + 0xf8n), memory.get(touch + 0xf8n));
}
hooks.get(base + 0x239b4c0n).onEnter([ptr(map)]);
assert.equal(destroyed.length, 2);
for (const deck of [3, 4]) {
  const data = memory.get(map + 0x140n + BigInt((((0xb0 + deck - 1) << 8) | 0x22) * 8));
  assert.equal(memory.get(data + 0xf8n), 0n);
}
// Refuse an occupied entry without allocating or overwriting it.
const thirdScratch = memory.get(map + 0x140n + BigInt(0xb222 * 8));
write(thirdScratch + 0xf8n, 0xbeefn);
assert.throws(() => sandbox.rpc.exports.activate('0x' + map.toString(16)), /ja possui/);
assert.equal(memory.get(thirdScratch + 0xf8n), 0xbeefn);
assert.equal(createdDecks.length, 2);
write(thirdScratch + 0xf8n, 0n);

// If the second native object fails verification, free both and bind nothing.
brokenDeck = 4;
assert.throws(() => sandbox.rpc.exports.activate('0x' + map.toString(16)), /deck incorreto/);
assert.equal(destroyed.length, 4);
assert.equal(memory.get(thirdScratch + 0xf8n), 0n);
console.log('Jog 3/4: validacao, criacao por deck, ligacoes e limpeza simuladas passaram.');
