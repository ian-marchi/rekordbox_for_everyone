'use strict';
// Temporary, version-bound experiment. MIDI mapping owns no processor here;
// this script owns the two processors until the device mapping is destroyed.
const rb = Process.getModuleByName('rekordbox.exe').base;
const expectedMapVtable = rb.add(0x3adc178);
const expectedRotateVtable = rb.add(0x3adf120);
const expectedTouchVtable = rb.add(0x3adf4c8);
const expectedProcessorVtable = rb.add(0x3ae4ae0);
const createProcessor = new NativeFunction(rb.add(0x23c11c0), 'pointer', ['int', 'double', 'double', 'int']);
const destroyProcessor = new NativeFunction(rb.add(0x23c5a90), 'pointer', ['pointer', 'int']);
let activeMap = null;
let allocated = [];
let bound = [];

function getData(map, key) { return map.add(0x140 + key * 8).readPointer(); }
function checkTemplate(map, deck) {
  const data = getData(map, (0xaf + deck) * 0x100 + 0x22);
  if (data.isNull() || !data.readPointer().equals(expectedRotateVtable) || data.add(8).readS32() !== deck)
    throw Error('Entrada de referencia do deck ' + deck + ' inesperada');
  const proc = data.add(0xf8).readPointer();
  if (proc.isNull() || !proc.readPointer().equals(expectedProcessorVtable) || proc.add(0x78).readS32() !== 3)
    throw Error('Processador de referencia do deck ' + deck + ' inesperado');
  const audio = proc.add(8).readPointer();
  if (audio.isNull() || audio.add(0x3ab30).readS32() !== deck)
    throw Error('Processador de audio nao corresponde ao deck ' + deck);
  const a = audio.add(0x3ab38).readDouble(), b = audio.add(0x3ab40).readDouble();
  if (Math.abs(a - 1.0) > 1e-9 || Math.abs(b - 2.1) > 1e-9)
    throw Error('Parametros do processador de referencia divergentes');
  return {a, b};
}
function prepare(map) {
  const result = [];
  for (const deck of [3, 4]) {
    const ch = deck - 1;
    for (const [kind, number] of [[0xb0, 0x22], [0xb0, 0x23], [0xb0, 0x21], [0xb0, 0x26],
                                   [0x90, 0x36], [0x90, 0x67]]) {
      const key = ((kind + ch) << 8) | number;
      const data = getData(map, key);
      const expected = kind === 0xb0 ? expectedRotateVtable : expectedTouchVtable;
      if (data.isNull() || !data.readPointer().equals(expected) || data.add(8).readS32() !== deck)
        throw Error('Mapeamento jog inesperado: ' + key.toString(16));
      if (!data.add(0xf8).readPointer().isNull())
        throw Error('Jog ja possui processador: ' + key.toString(16));
      result.push({deck, key, data});
    }
  }
  return result;
}
function cleanup() {
  for (const item of bound) {
    try {
      if (item.data.add(0xf8).readPointer().equals(item.processor)) item.data.add(0xf8).writePointer(ptr(0));
    } catch (e) { send('cleanup mapping error: ' + e); }
  }
  bound = [];
  for (const proc of allocated) {
    try {
      if (proc.readPointer().equals(expectedProcessorVtable)) destroyProcessor(proc, 1);
    } catch (e) { send('cleanup processor error: ' + e); }
  }
  allocated = [];
  activeMap = null;
}
Interceptor.attach(rb.add(0x239b4c0), {
  onEnter(args) {
    if (activeMap && args[0].equals(activeMap)) {
      cleanup();
      send('jog34: recursos liberados ao desconectar');
    }
  }
});
rpc.exports = {
  activate(mapAddress) {
    if (activeMap) throw Error('Teste ja esta ativo');
    const map = ptr(mapAddress);
    if (!map.readPointer().equals(expectedMapVtable)) throw Error('Mapa de controlador mudou');
    const left = checkTemplate(map, 1), right = checkTemplate(map, 2);
    const targets = prepare(map);
    try {
      for (const deck of [3, 4]) {
        const t = deck === 3 ? left : right;
        const proc = createProcessor(deck, t.a, t.b, 3);
        if (proc.isNull()) throw Error('Nao foi possivel criar processador do deck ' + deck);
        allocated.push(proc);
        if (!proc.readPointer().equals(expectedProcessorVtable) || proc.add(0x78).readS32() !== 3)
          throw Error('Tipo de processador criado inesperado');
        const audio = proc.add(8).readPointer();
        if (audio.isNull() || audio.add(0x3ab30).readS32() !== deck)
          throw Error('Processador criado para deck incorreto');
        const latency = map.add(0x809f8).readS32();
        const setLatency = new NativeFunction(proc.readPointer().add(8).readPointer(), 'void', ['pointer', 'int']);
        setLatency(proc, latency);
      }
      for (const target of targets) {
        const processor = allocated[target.deck - 3];
        target.data.add(0xf8).writePointer(processor);
        bound.push({data: target.data, processor});
      }
      activeMap = map;
      send('jog34: processadores criados e associados a ' + bound.length + ' entradas');
      return {decks: [3, 4], bindings: bound.length, status: 'active'};
    } catch (e) {
      cleanup();
      throw e;
    }
  },
  dispose() { cleanup(); return 'cleaned'; }
};
