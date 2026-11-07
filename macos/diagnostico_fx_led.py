#!/usr/bin/env python3
"""Observa MIDI de FX e pads na copia REV1 Stems do rekordbox 6.8.5 Intel."""
import json
from pathlib import Path
import subprocess
import sys
import threading

import diagnostico_jogs
import install

HERE = Path(__file__).resolve().parent
METHODS = {0x150dd60: bytes.fromhex('554889e5415741564155415453'),
           0x1bdecc0: bytes.fromhex('554889e5415741564155415453')}


def main():
    if sys.platform != 'darwin':
        raise RuntimeError('Execute no Mac com o rekordbox REV1 Stems aberto.')
    import frida
    executable = install.inspect_app(install.STEMS_DESTINATION).resolve(strict=True)
    diagnostico_jogs.check_executable(executable)
    binary = executable.read_bytes()
    if any(binary[offset:offset + len(expected)] != expected for offset, expected in METHODS.items()):
        raise ValueError('Metodos MIDI diferentes do build analisado.')
    device = frida.get_local_device()
    processes = [p.pid for p in device.enumerate_processes() if p.name == 'rekordbox']
    if len(processes) != 1:
        raise RuntimeError('Abra somente a copia REV1 Stems e tente novamente.')
    process_path = subprocess.run(['/bin/ps', '-p', str(processes[0]), '-o', 'comm='],
                                  capture_output=True, text=True, check=True).stdout.strip()
    if Path(process_path).resolve() != executable:
        raise RuntimeError('O processo aberto nao e a copia REV1 Stems esperada.')
    done = threading.Event()
    session = device.attach(processes[0])
    session.on('detached', lambda *args: done.set())
    try:
        script = session.create_script((HERE / 'diagnostico_fx_led.js').read_text(encoding='utf-8'))
        script.on('message', lambda message, data: print(json.dumps(
            message.get('payload', message), ensure_ascii=False), flush=True))
        script.load()
        print('Por 45 segundos, pressione FX 1, a alavanca, e os tres pads de stems.', flush=True)
        done.wait(45)
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
