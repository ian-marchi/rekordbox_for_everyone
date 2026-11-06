"""Start the locally patched rekordbox 7.2.14 with the REV1 USB lookup fix.

This process must remain running while rekordbox runs. The intervention is
restricted to the FLX4 USB-version lookup and does not modify the executable.
"""
import datetime
import hashlib
import os
from pathlib import Path
import sys
import threading

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / 'frida_runtime'))
import frida

EXE = Path(r'C:\Program Files\rekordbox\rekordbox 7.2.14\rekordbox.exe')
EXPECTED_SHA256 = 'f96386b16ec36c9f319c16a14afb47abbe73c5aaeb9b49165a855f692476fb70'
LOG = HERE / 'rev1_launcher.log'
SCRIPT = r'''
'use strict';
const rbModule = Process.getModuleByName('rekordbox.exe');
Interceptor.attach(rbModule.base.add(0x1d268d0), {
  onEnter(args) {
    if (args[0].toUInt32() === 0x2b73 && args[1].toUInt32() === 0x45) {
      args[1] = ptr(0x3f);
      send('USB lookup FLX4 redirected to REV1');
    }
  }
});
send('USB lookup hook installed');
'''

def log(message):
    line = f'{datetime.datetime.now().isoformat(timespec="seconds")} {message}'
    with LOG.open('a', encoding='utf-8') as out:
        out.write(line + '\n')
    print(line, flush=True)

def main():
    if not EXE.is_file():
        raise RuntimeError(f'Executavel nao encontrado: {EXE}')
    digest = hashlib.sha256(EXE.read_bytes()).hexdigest()
    if digest != EXPECTED_SHA256:
        raise RuntimeError('O executavel nao e a versao testada. O launcher nao sera aplicado.')
    device = frida.get_local_device()
    running = [p.pid for p in device.enumerate_processes() if p.name.lower() == 'rekordbox.exe']
    if running:
        raise RuntimeError(f'Feche o rekordbox antes de usar o launcher. Processos: {running}')

    session = None
    pid = None
    resumed = False
    done = threading.Event()
    try:
        pid = device.spawn([str(EXE)], cwd=str(EXE.parent))
        log(f'rekordbox iniciado com PID {pid}, preparando correcao em memoria')
        session = device.attach(pid)
        session.on('detached', lambda *args: done.set())
        script = session.create_script(SCRIPT)
        script.on('message', lambda message, data: log(str(message.get('payload', message))))
        script.load()
        device.resume(pid)
        resumed = True
        log('rekordbox iniciado; mantenha esta janela aberta durante o uso')
        done.wait()
        log('rekordbox encerrado ou sessao de diagnostico desconectada')
    finally:
        if pid is not None and not resumed:
            try:
                device.kill(pid)
                log('processo suspenso encerrado apos falha na preparacao')
            except Exception as exc:
                log(f'erro ao encerrar processo suspenso: {exc}')
        if session is not None:
            try:
                session.detach()
            except frida.InvalidOperationError:
                pass

if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        log(f'ERRO: {exc}')
        sys.exit(1)
