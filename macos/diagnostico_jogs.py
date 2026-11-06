#!/usr/bin/env python3
"""Observa eventos dos jogs no rekordbox REV1 6.8.5 Intel por 45 segundos."""
import json
from pathlib import Path
import subprocess
import sys
import threading

import install

HERE = Path(__file__).resolve().parent
METHODS = {
    0x1117de0: bytes.fromhex('554889e5415741565350'),
    0x1118650: bytes.fromhex('554889e5415741565350'),
}


def check_executable(executable):
    data = executable.read_bytes()
    if data[install.NAME_OFFSET:install.NAME_OFFSET + 9] != b'DDJ-REV1\0':
        raise ValueError('A copia REV1 esperada nao foi encontrada.')
    if any(data[offset - 5:offset + 6] != bytes.fromhex('554889e5b83f0000005dc3')
           for offset in install.PID_OFFSETS):
        raise ValueError('As instrucoes USB da copia REV1 sao diferentes das esperadas.')
    if any(data[offset:offset + len(expected)] != expected for offset, expected in METHODS.items()):
        raise ValueError('Metodos dos jogs nao correspondem ao build analisado.')


def main():
    if sys.platform != 'darwin':
        raise RuntimeError('Execute no Mac Intel com o rekordbox REV1 aberto.')
    import frida
    executable = install.inspect_app(install.DESTINATION).resolve(strict=True)
    check_executable(executable)
    device = frida.get_local_device()
    candidates = [p.pid for p in device.enumerate_processes() if p.name == 'rekordbox']
    if len(candidates) != 1:
        raise RuntimeError('Abra somente a copia rekordbox REV1 e tente novamente.')
    process_path = subprocess.run(['/bin/ps', '-p', str(candidates[0]), '-o', 'comm='],
                                  capture_output=True, text=True, check=True).stdout.strip()
    if Path(process_path).resolve() != executable:
        raise RuntimeError('O processo aberto nao e a copia REV1 esperada.')
    detached = threading.Event()
    session = device.attach(candidates[0])
    session.on('detached', lambda *args: detached.set())
    script = session.create_script((HERE / 'diagnostico_jogs.js').read_text(encoding='utf-8'))
    def message(value, data):
        if value.get('type') == 'send':
            print(json.dumps(value['payload'], ensure_ascii=False), flush=True)
        else:
            print(json.dumps(value, ensure_ascii=False), flush=True)
    script.on('message', message)
    try:
        script.load()
        print('Durante 45 segundos, gire e toque nos jogs dos decks 1, 2, 3 e 4.', flush=True)
        detached.wait(45)
    finally:
        try:
            session.detach()
        except frida.InvalidOperationError:
            pass
    print('Diagnostico encerrado.')


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print(f'ERRO: {exc}', file=sys.stderr)
        sys.exit(1)
