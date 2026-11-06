'use strict';
const base = Process.getModuleByName('rekordbox.exe').base;
const expectedVtable = base.add(0x3adc178);
const pattern = expectedVtable.toMatchPattern();
const maps = [0xb022, 0xb122, 0xb222, 0xb322, 0xb021, 0xb221, 0xb121, 0xb321, 0x9036, 0x9236, 0x9136, 0x9336];
let scanned = 0, found = 0;
let ranges = Process.enumerateRanges({protection: 'rw-', coalesce: true})
  .filter(r => r.size >= 0x80da0)
  .sort((a, b) => a.size - b.size);
function detail(object) {
  const out = {};
  for (const key of maps) {
    try {
      const data = object.add(0x140 + key * 8).readPointer();
      if (data.isNull()) { out[key.toString(16)] = null; continue; }
      let name = '';
      try { name = data.add(0x10).readPointer().readUtf8String(); } catch (_) {}
      out[key.toString(16)] = {data: data.toString(), type: data.readPointer().toString(),
        number: data.add(8).readS32(), name,
        target: data.add(0x150).readPointer().toString()};
    } catch (e) { out[key.toString(16)] = 'unreadable'; }
  }
  return out;
}
function next() {
  if (!ranges.length || scanned >= 1024 * 1024 * 1024 || found >= 4) {
    send(JSON.stringify({stage: 'done', scanned, found, remaining: ranges.length}));
    return;
  }
  const r = ranges.shift();
  const length = Math.min(r.size, 128 * 1024 * 1024);
  scanned += length;
  Memory.scan(r.base, length, pattern, {
    onMatch(address) {
      try {
        const entries = detail(address);
        if (entries.b022 && entries.b222) {
          found++;
          send(JSON.stringify({stage: 'map', address: address.toString(), entries}));
        }
      } catch (_) {}
    },
    onError(reason) { send('scan error: ' + reason); },
    onComplete() { setImmediate(next); }
  });
}
send('jog mapping scan ready');
setImmediate(next);
