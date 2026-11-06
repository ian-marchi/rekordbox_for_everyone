"""Ativa o experimento de jogs no rekordbox ja aberto; mantenha esta janela aberta."""
import hashlib
import json
from pathlib import Path
import sys
import threading

import frida

HERE = Path(__file__).resolve().parent
EXE = Path(r'C:\Program Files\rekordbox\rekordbox 7.2.14\rekordbox.exe')
EXPECTED = 'f96386b16ec36c9f319c16a14afb47abbe73c5aaeb9b49165a855f692476fb70'


def main():
    if hashlib.sha256(EXE.read_bytes()).hexdigest() != EXPECTED:
        raise RuntimeError('O executavel nao corresponde a versao testada.')
    device = frida.get_local_device()
    processes = [p.pid for p in device.enumerate_processes() if p.name.lower() == 'rekordbox.exe']
    if len(processes) != 1:
        raise RuntimeError('Abra exatamente uma instancia do rekordbox pelo launcher.')
    completed = threading.Event()
    detached = threading.Event()
    maps = []
    session = device.attach(processes[0])
    session.on('detached', lambda *args: (completed.set(), detached.set()))
    scanner = None
    trial = None
    active = False
    try:
        scanner = session.create_script((HERE / 'inspect_jog_mapping_live.js').read_text(encoding='utf-8'))
        def on_scan(message, data):
            if message.get('type') == 'error':
                print(message, flush=True)
                completed.set()
                return
            try:
                item = json.loads(message.get('payload', ''))
                if item.get('stage') == 'map':
                    maps.append(item['address'])
                elif item.get('stage') == 'done':
                    completed.set()
            except (ValueError, TypeError):
                pass
        scanner.on('message', on_scan)
        scanner.load()
        print('Procurando o mapa da REV1; aguarde...', flush=True)
        if not completed.wait(60) or len(maps) != 1 or detached.is_set():
            raise RuntimeError(f'Mapa nao encontrado de forma unica ({len(maps)}). Reconecte a REV1 e tente novamente.')
        scanner.unload()
        scanner = None
        trial = session.create_script((HERE / 'jog34_live_trial.js').read_text(encoding='utf-8'))
        trial.on('message', lambda message, data: print(message.get('payload', message), flush=True))
        trial.load()
        print(trial.exports_sync.activate(maps[0]), flush=True)
        active = True
        print('Jogs 3/4 ativos. Mantenha esta janela aberta; feche o rekordbox ao terminar.', flush=True)
        detached.wait()
        active = False
    finally:
        if active and trial is not None and not detached.is_set():
            print('Desativando os jogs experimentais...', flush=True)
            trial.exports_sync.dispose()
        try:
            session.detach()
        except frida.InvalidOperationError:
            pass


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print(f'ERRO: {exc}', file=sys.stderr)
        sys.exit(1)
