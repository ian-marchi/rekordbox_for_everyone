#!/usr/bin/env python3
"""Cria uma copia REV1 separada para diagnostico com get-task-allow."""
import os
from pathlib import Path
import plistlib
import shutil
import subprocess
import sys
import tempfile

import diagnostico_jogs
import install

DESTINATION = Path.home() / 'Applications' / 'rekordbox REV1 Diagnostico 6.8.5.app'
ALLOW = 'com.apple.security.get-task-allow'


def debug_entitlements(raw):
    entitlements = plistlib.loads(raw)
    if not isinstance(entitlements, dict):
        raise ValueError('Entitlements da copia REV1 inesperados.')
    entitlements[ALLOW] = True
    return plistlib.dumps(entitlements)


def read_entitlements(app):
    result = subprocess.run(['/usr/bin/codesign', '-d', '--entitlements', ':-', str(app)],
                            capture_output=True, check=True)
    return plistlib.loads(result.stdout)


def main():
    if sys.platform != 'darwin':
        raise RuntimeError('Execute no macOS.')
    if subprocess.run(['/usr/bin/pgrep', '-x', 'rekordbox'], capture_output=True).returncode == 0:
        raise RuntimeError('Feche o rekordbox antes de preparar a copia de diagnostico.')
    source = install.STEMS_DESTINATION.resolve(strict=True)
    executable = install.inspect_app(source)
    diagnostico_jogs.check_executable(executable)
    subprocess.run(['/usr/bin/codesign', '--verify', '--deep', '--strict', str(source)], check=True)
    original_entitlements = read_entitlements(source)
    if not isinstance(original_entitlements, dict):
        raise ValueError('Entitlements da copia REV1 inesperados.')
    desired = plistlib.loads(debug_entitlements(plistlib.dumps(original_entitlements)))
    if DESTINATION.exists():
        raise FileExistsError('A copia de diagnostico ja existe; nao sera substituida: ' + str(DESTINATION))
    DESTINATION.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix='.rev1-diagnostico-', dir=str(DESTINATION.parent)))
    try:
        staged = staging / DESTINATION.name
        entitlements_path = staging / 'entitlements.plist'
        entitlements_path.write_bytes(plistlib.dumps(desired))
        subprocess.run(['/usr/bin/ditto', str(source), str(staged)], check=True)
        subprocess.run(['/usr/bin/codesign', '--force', '--sign', '-',
                        '--preserve-metadata=flags,runtime', '--entitlements', str(entitlements_path),
                        str(staged)], check=True)
        subprocess.run(['/usr/bin/codesign', '--verify', '--deep', '--strict', str(staged)], check=True)
        if read_entitlements(staged) != desired:
            raise RuntimeError('Permissoes da copia assinada diferem do esperado.')
        diagnostico_jogs.check_executable(install.inspect_app(staged))
        os.rename(staged, DESTINATION)
        print('Copia de diagnostico criada:', DESTINATION)
    finally:
        shutil.rmtree(staging, ignore_errors=True)


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as exc:
        print('ERRO:', exc, file=sys.stderr)
        sys.exit(1)
