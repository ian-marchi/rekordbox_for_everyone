#!/usr/bin/env python3
"""Instalador experimental para o rekordbox 6.8.5.0002 para macOS x86-64."""
import argparse
import hashlib
import os
from pathlib import Path
import plistlib
import shutil
import subprocess
import sys
import tempfile
import time

HERE = Path(__file__).resolve().parent
DEFAULT_APP = Path('/Applications/rekordbox 6/rekordbox.app')
DESTINATION = Path.home() / 'Applications' / 'rekordbox REV1 6.8.5.app'
ORIGINAL_SHA256 = 'ba9a80ea5fdb01f1981d8b05cc6b35c9b9bd480919aab58184ea3c89b90f50c5'
PATCHED_SHA256 = '15c0752720562f7658c72ee2f0ef47f50132b9196d3013431be787ef83f012d9'
MAPPING_SHA256 = 'd2e95ba0a2cd4f29a3a06ef0478d4a587eb7da845504ecbfed4f5e5a35b88fcc'
VERSION = '6.8.5.0002'
NAME_OFFSET = 0x3eb1b23
PID_OFFSETS = (0xff82b5, 0xff8815)
GETTER_PREFIX = bytes.fromhex('554889e5b8450000005dc3')
MAP_NAME = 'DDJ-REV1.midi.csv'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def patch_binary(original):
    """Only patch the exact, statically examined Intel build."""
    if digest(original) != ORIGINAL_SHA256:
        raise ValueError('SHA-256 do executavel nao corresponde ao build analisado.')
    if original[NAME_OFFSET:NAME_OFFSET + 9] != b'DDJ-FLX4\0':
        raise ValueError('Nome FLX4 nao encontrado no local esperado.')
    if original.count(b'DDJ-FLX4\0') != 1:
        raise ValueError('Quantidade inesperada de nomes FLX4.')
    for offset in PID_OFFSETS:
        if original[offset - 5:offset + 6] != GETTER_PREFIX:
            raise ValueError('Uma instrucao PID nao corresponde ao build analisado.')
    out = bytearray(original)
    out[NAME_OFFSET:NAME_OFFSET + 8] = b'DDJ-REV1'
    for offset in PID_OFFSETS:
        out[offset] = 0x3f
    if digest(out) != PATCHED_SHA256:
        raise ValueError('Hash do executavel modificado inesperado.')
    return out


def mapping_data():
    path = HERE / MAP_NAME
    data = path.read_bytes()
    if digest(data) != MAPPING_SHA256:
        raise ValueError('Mapeamento ausente ou alterado; nao sera instalado.')
    return data


def inspect_app(app):
    info = app / 'Contents' / 'Info.plist'
    with info.open('rb') as stream:
        plist = plistlib.load(stream)
    if plist.get('CFBundleIdentifier') != 'com.pioneerdj.rekordboxdj':
        raise ValueError('O aplicativo selecionado nao e o rekordbox esperado.')
    if plist.get('CFBundleShortVersionString') != VERSION:
        raise ValueError(f'Versao esperada: {VERSION}; encontrada: {plist.get("CFBundleShortVersionString")}')
    executable = plist.get('CFBundleExecutable')
    if executable != 'rekordbox':
        raise ValueError('Nome de executavel inesperado.')
    return app / 'Contents' / 'MacOS' / executable


def existing_user_maps():
    # Caminhos conhecidos; nao varrer outras pastas ou bibliotecas do usuario.
    home = Path.home()
    bases = [home / 'Library' / 'Pioneer' / 'rekordbox6',
             home / 'Library' / 'Application Support' / 'Pioneer' / 'rekordbox6']
    return [base / 'MidiMappings' / MAP_NAME for base in bases
            if (base / 'MidiMappings' / MAP_NAME).is_file()]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--app', type=Path, default=DEFAULT_APP,
                        help='Caminho do rekordbox.app original')
    parser.add_argument('--check', action='store_true',
                        help='Verificar compatibilidade sem modificar arquivos')
    args = parser.parse_args(argv)
    if sys.platform != 'darwin':
        raise RuntimeError('Execute este instalador em um Mac com macOS.')
    if subprocess.run(['/usr/bin/pgrep', '-x', 'rekordbox'], capture_output=True).returncode == 0:
        raise RuntimeError('Feche o rekordbox antes de instalar ou verificar.')
    app = args.app.expanduser().resolve(strict=True)
    executable = inspect_app(app)
    patched = patch_binary(executable.read_bytes())
    mapping = mapping_data()
    print('Build Intel 6.8.5.0002 e mapeamento: verificados.')
    overrides = existing_user_maps()
    for item in overrides:
        print(f'Mapeamento anterior a preservar: {item}')
    if args.check:
        print('Verificacao concluida; nenhum arquivo foi alterado.')
        return
    if DESTINATION.exists():
        raise FileExistsError(f'Destino ja existe; nao sera sobrescrito: {DESTINATION}')
    DESTINATION.parent.mkdir(parents=True, exist_ok=True)
    staging_root = Path(tempfile.mkdtemp(prefix='.rev1-install-', dir=str(DESTINATION.parent)))
    staged_app = staging_root / DESTINATION.name
    changed_overrides = []
    installed = False
    try:
        print('Copiando aplicativo; o original sera preservado...')
        subprocess.run(['/usr/bin/ditto', str(app), str(staged_app)], check=True)
        staged_exe = inspect_app(staged_app)
        if digest(staged_exe.read_bytes()) != ORIGINAL_SHA256:
            raise ValueError('A copia do executavel nao corresponde ao original.')
        staged_exe.write_bytes(patched)
        resource_dir = staged_app / 'Contents' / 'Resources' / 'MidiMappings'
        if not resource_dir.is_dir():
            raise RuntimeError('Pasta de mapeamentos nao encontrada na copia.')
        (resource_dir / MAP_NAME).write_bytes(mapping)
        print('Assinando localmente a copia do aplicativo...')
        subprocess.run(['/usr/bin/codesign', '--force', '--deep', '--sign', '-',
                        '--preserve-metadata=entitlements,flags,runtime', str(staged_app)], check=True)
        subprocess.run(['/usr/bin/codesign', '--verify', '--deep', '--strict', str(staged_app)], check=True)
        # codesign atualiza a assinatura embutida do Mach-O; o hash completo
        # pode mudar, mas as tres alteracoes de codigo/dados devem permanecer.
        signed = staged_exe.read_bytes()
        if signed[NAME_OFFSET:NAME_OFFSET + 9] != b'DDJ-REV1\0':
            raise RuntimeError('Nome REV1 nao encontrado apos a assinatura.')
        if any(signed[offset - 5:offset + 6] != bytes.fromhex('554889e5b83f0000005dc3')
               for offset in PID_OFFSETS):
            raise RuntimeError('Uma instrucao PID mudou apos a assinatura.')
        # Sempre preservar os mapas pessoais existentes antes de qualquer substituicao.
        for old in overrides:
            if digest(old.read_bytes()) == MAPPING_SHA256:
                continue
            backup = old.with_name(old.name + '.before-rev1-' + str(time.time_ns()) + '.backup')
            with backup.open('xb') as stream:
                stream.write(old.read_bytes())
            changed_overrides.append((old, backup))
            old.write_bytes(mapping)
            print(f'Backup do mapeamento anterior: {backup}')
        os.rename(staged_app, DESTINATION)
        installed = True
        print(f'Instalado: {DESTINATION}')
        print('Abra a COPIA instalada, com a REV1 conectada.')
        print('Instalacao experimental: o funcionamento no Mac ainda precisa ser testado.')
    finally:
        if not installed:
            for old, backup in reversed(changed_overrides):
                try:
                    old.write_bytes(backup.read_bytes())
                except OSError as exc:
                    print(f'Falha ao restaurar {old}; backup preservado em {backup}: {exc}', file=sys.stderr)
        shutil.rmtree(staging_root, ignore_errors=True)


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as exc:
        print(f'ERRO: {exc}', file=sys.stderr)
        sys.exit(1)
