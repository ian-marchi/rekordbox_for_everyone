"""Preparar o rekordbox 7.2.14 Windows x64 para o launcher REV1."""
import argparse
import hashlib
import os
from pathlib import Path
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
APP = Path(r'C:\Program Files\rekordbox\rekordbox 7.2.14')
EXE = APP / 'rekordbox.exe'
BACKUP = APP / 'rekordbox.exe.bak_REV1'
MAPPING = APP / 'MidiMappings' / 'DDJ-REV1.midi.csv'
ORIGINAL = 'f6359b6b3553e5f81e55444b28b7b56aa6f80f7bb7eb88f3c84d865d821ad5a9'
PATCHED = 'f96386b16ec36c9f319c16a14afb47abbe73c5aaeb9b49165a855f692476fb70'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def patch_binary(data):
    if digest(data) != ORIGINAL or data.count(b'DDJ-FLX4') != 39:
        raise ValueError('Executavel original diferente do build verificado.')
    result = data.replace(b'DDJ-FLX4', b'DDJ-REV1')
    if digest(result) != PATCHED:
        raise ValueError('Hash inesperado do executavel modificado.')
    return result


def replace_atomic(path, data):
    fd, name = tempfile.mkstemp(prefix='.rev1-', dir=str(path.parent))
    try:
        with os.fdopen(fd, 'wb') as out:
            out.write(data)
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='somente verificar, sem alterar arquivos')
    args = parser.parse_args()
    if sys.platform != 'win32':
        raise RuntimeError('Execute no Windows.')
    processes = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq rekordbox.exe', '/NH'],
                               capture_output=True, text=True, check=True)
    if 'rekordbox.exe' in processes.stdout.lower():
        raise RuntimeError('Feche o rekordbox antes de instalar ou verificar.')
    current = EXE.read_bytes()
    h = digest(current)
    patched = patch_binary(current) if h == ORIGINAL else current if h == PATCHED else None
    if patched is None:
        raise ValueError('Versao ou hash do executavel nao reconhecido.')
    mapping = (HERE / 'DDJ-REV1.midi.csv').read_bytes()
    if MAPPING.exists() and MAPPING.read_bytes() != mapping:
        raise ValueError(f'Mapeamento ja existe e e diferente: {MAPPING}; preserve-o antes de continuar.')
    if BACKUP.exists() and digest(BACKUP.read_bytes()) != ORIGINAL:
        raise ValueError(f'Backup existente nao corresponde ao original: {BACKUP}')
    if h == PATCHED and not BACKUP.exists():
        raise ValueError('Executavel ja modificado, mas backup original nao foi encontrado.')
    print('Executavel e mapeamento compativeis.')
    if args.check:
        print('Nenhum arquivo foi alterado.')
        return
    if h == ORIGINAL and not BACKUP.exists():
        with BACKUP.open('xb') as out:
            out.write(current)
        print(f'Backup criado: {BACKUP}')
    created_map = False
    try:
        if not MAPPING.exists():
            with MAPPING.open('xb') as out:
                out.write(mapping)
            created_map = True
        if h == ORIGINAL:
            replace_atomic(EXE, patched)
        print('Instalado. Inicie usando windows/iniciar.cmd.')
    except Exception:
        if created_map and MAPPING.exists() and MAPPING.read_bytes() == mapping:
            MAPPING.unlink()
        raise


if __name__ == '__main__':
    try:
        main()
    except (OSError, RuntimeError, ValueError, subprocess.CalledProcessError) as exc:
        print(f'ERRO: {exc}', file=sys.stderr)
        sys.exit(1)
