/* Observacao temporaria e restrita a mensagens de FX e pads no 6.8.5 Intel. */
'use strict';
const base = Process.getModuleByName('rekordbox').base;
let count = 0;
function observe(direction, message, device) {
  try {
    if (message.add(0x10).readS32() !== 3 || count >= 250) return;
    const allocated = message.add(8).readPointer();
    const bytes = allocated.isNull() ? message.add(0x14) : allocated;
    const status = bytes.readU8(), control = bytes.add(1).readU8(), value = bytes.add(2).readU8();
    const fx = (status === 0x94 || status === 0x95) &&
      (control === 0x50 || control === 0x06 || control === 0x07 || (control >= 0x70 && control <= 0x72));
    // Include both bytes of the known high-resolution depth controls.
    const depth = (status === 0xb4 || status === 0xb5) && (control === 0x02 || control === 0x22);
    const mixer = status === 0xb6 && [0x08, 0x28, 0x0d, 0x2d].includes(control);
    const cue = (status === 0x96 && control === 0x63) ||
      (status >= 0x90 && status <= 0x93 && control === 0x54);
    const pad = status >= 0x90 && status <= 0x9f &&
      ((control >= 0x30 && control <= 0x37) || (direction === 'entrada' && control <= 7));
    const mode = status >= 0x90 && status <= 0x93 && control === 0x22;
    if (!fx && !depth && !mixer && !cue && !pad && !mode) return;
    count++;
    let nome = 'indisponivel';
    try {
      const offset = direction === 'entrada' ? 8 : 0x160;
      const text = device.add(offset).readPointer();
      if (!text.isNull()) nome = text.readUtf8String();
    } catch (_) {}
    send({direcao: direction, status: status.toString(16).padStart(2, '0'),
      controle: control.toString(16).padStart(2, '0'), valor: value, porta: nome});
  } catch (error) { send({erro: String(error)}); }
}
Interceptor.attach(base.add(0x150dd60), {onEnter(args) { observe('entrada', args[2], args[1]); }});
Interceptor.attach(base.add(0x1bdecc0), {onEnter(args) { observe('saida', args[1], args[0]); }});
send({estado: 'pronto'});
