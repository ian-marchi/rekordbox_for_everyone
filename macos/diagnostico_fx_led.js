/* Observacao temporaria e restrita a mensagens de FX e pads no 6.8.5 Intel. */
'use strict';
const base = Process.getModuleByName('rekordbox').base;
let count = 0;
function observe(direction, message) {
  try {
    if (message.add(0x10).readS32() !== 3 || count >= 250) return;
    const allocated = message.add(8).readPointer();
    const bytes = allocated.isNull() ? message.add(0x14) : allocated;
    const status = bytes.readU8(), control = bytes.add(1).readU8(), value = bytes.add(2).readU8();
    const fx = (status === 0x94 || status === 0x95) &&
      (control === 0x50 || control === 0x06 || control === 0x07 || (control >= 0x70 && control <= 0x72));
    const pad = status >= 0x90 && status <= 0x9f && control >= 0x30 && control <= 0x32;
    const mode = status >= 0x90 && status <= 0x93 && control === 0x22;
    if (!fx && !pad && !mode) return;
    count++;
    send({direcao: direction, status: status.toString(16).padStart(2, '0'),
      controle: control.toString(16).padStart(2, '0'), valor: value});
  } catch (error) { send({erro: String(error)}); }
}
Interceptor.attach(base.add(0x150dd60), {onEnter(args) { observe('entrada', args[2]); }});
Interceptor.attach(base.add(0x1bdecc0), {onEnter(args) { observe('saida', args[1]); }});
send({estado: 'pronto'});
