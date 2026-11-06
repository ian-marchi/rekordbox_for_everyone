/* Observacao temporaria: rekordbox 6.8.5.0002 Intel. Nao altera o mapeamento. */
'use strict';
const base = Process.getModuleByName('rekordbox').base;
const seen = new Set();
function watch(offset, kind) {
  Interceptor.attach(base.add(offset), {
    onEnter(args) {
      try {
        const deck = args[0].add(8).readS32();
        const processor = !args[0].add(0x110).readPointer().isNull();
        if (deck < 1 || deck > 4) return;
        const key = kind + ':' + deck + ':' + processor;
        if (!seen.has(key)) {
          seen.add(key);
          send({controle: kind, deck: deck, processador_presente: processor});
        }
      } catch (error) { send({erro: String(error)}); }
    }
  });
}
watch(0x1117de0, 'giro');
watch(0x1118650, 'toque');
send({estado: 'pronto'});
