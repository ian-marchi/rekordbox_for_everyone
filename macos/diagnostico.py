#!/usr/bin/env python3
"""Diagnostico somente de leitura da instalacao experimental."""
from pathlib import Path
import platform
import subprocess
import sys

import install


def command(args):
    try:
        return subprocess.run(args, capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.TimeoutExpired):
        return None


def main():
    if sys.platform != 'darwin':
        raise RuntimeError('Execute no Mac.')
    model = command(['/usr/sbin/sysctl', '-n', 'hw.model'])
    print('Modelo:', model.stdout.strip() if model and model.returncode == 0 else 'indisponivel')
    print('macOS:', platform.mac_ver()[0], '| arquitetura:', platform.machine())
    print('Python:', platform.python_version())
    for label, app in [('Original', install.DEFAULT_APP), ('Copia REV1', install.DESTINATION)]:
        print(f'{label}:', 'encontrado' if app.is_dir() else 'nao encontrado')
        if not app.is_dir():
            continue
        try:
            exe = install.inspect_app(app)
            binary = exe.read_bytes()
            print('  Build esperado:', 'sim')
            if label == 'Original':
                print('  Hash original compativel:', 'sim' if install.digest(binary) == install.ORIGINAL_SHA256 else 'nao')
            else:
                name_ok = binary[install.NAME_OFFSET:install.NAME_OFFSET + 9] == b'DDJ-REV1\0'
                pid_ok = all(binary[o-5:o+6] == bytes.fromhex('554889e5b83f0000005dc3') for o in install.PID_OFFSETS)
                print('  Alteracoes esperadas:', 'sim' if name_ok and pid_ok else 'nao')
                signed = command(['/usr/bin/codesign', '--verify', '--deep', '--strict', str(app)])
                print('  Assinatura local valida:', 'sim' if signed and signed.returncode == 0 else 'nao')
        except (OSError, ValueError) as exc:
            print('  Erro ao inspecionar:', exc)
    usb = command(['/usr/sbin/ioreg', '-p', 'IOUSB', '-l'])
    print('REV1 visivel na arvore USB:', 'sim' if usb and 'DDJ-REV1' in usb.stdout else 'nao identificada')
    print('Mapeamentos pessoais existentes:', len(install.existing_user_maps()))


if __name__ == '__main__':
    try:
        main()
    except RuntimeError as exc:
        print(f'ERRO: {exc}', file=sys.stderr)
        sys.exit(1)
