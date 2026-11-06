"""Launcher experimental para os controles FX/CUE da REV1 no rekordbox 7.2.14."""
import csv
from datetime import datetime
import hashlib
import io
import os
from pathlib import Path
import sys
import tempfile

import rev1_launcher as base

HERE = Path(__file__).resolve().parent
MAPPING = Path(os.environ['APPDATA']) / 'Pioneer' / 'rekordbox6' / 'MidiMappings' / 'DDJ-REV1.midi.csv'


def prepare_mapping(original):
    text = original.decode('utf-8-sig')
    rows = list(csv.reader(io.StringIO(text, newline='')))
    if not rows or rows[0][:3] != ['@file', '1', 'DDJ-REV1']:
        raise ValueError('Cabecalho MIDI REV1 inesperado.')
    for side, channel in ((1, '94'), (2, '95')):
        for slot in range(1, 4):
            function = f'FX{side}-{slot}On'
            code = f'{channel}{0x6f + slot:02X}'
            if not any(len(r) > 3 and r[1] == function and r[3].upper() == code for r in rows):
                raise ValueError(f'Mapeamento esperado nao encontrado: {function} = {code}.')
    for side, channel in ((1, '94'), (2, '95')):
        for direction, note in (('Down', '06'), ('Up', '07')):
            function, code = f'FX{side}-1Beat{direction}', channel + note
            if not any(len(r) > 3 and r[1] == function and r[3].upper() == code for r in rows):
                raise ValueError(f'Mapeamento esperado nao encontrado: {function} = {code}.')
    beat_rows = []
    for side, channel in ((1, '94'), (2, '95')):
        for slot, direction, note in ((2, 'Down', '7A'), (3, 'Down', '7B'),
                                      (2, 'Up', '7C'), (3, 'Up', '7D')):
            beat_rows.append((channel + note, f'FX{side}-{slot}Beat{direction}'))
    wanted = {'B60C': 'HeadphonesMix', '9663': 'MasterCue', **dict(beat_rows)}
    found = set()
    for r in rows:
        if len(r) <= 3 or r[0].startswith('#'):
            continue
        code = r[3].upper()
        if code in wanted:
            if r[1] != wanted[code]:
                raise ValueError(f'O codigo {code} ja esta atribuido a outra funcao.')
            found.add(code)
    if found == set(wanted):
        return original, False
    newline = '\r\n' if b'\r\n' in original else '\n'
    output = io.StringIO(newline='')
    writer = csv.writer(output, lineterminator=newline)
    if 'B60C' not in found:
        writer.writerow(['HeadphonesMix', 'HeadphonesMix', 'KnobSliderHiRes', 'B60C',
                         '', '', '', '', '', '', '', '', '', '', 'FX/CUE: mistura de fone'])
    if '9663' not in found:
        writer.writerow(['MasterCue', 'MasterCue', 'Button', '9663', '', '', '', '',
                         '9663', '', '', '', '', '', 'FX/CUE: monitorar master'])
    for code, function in beat_rows:
        if code not in found:
            writer.writerow([function, function, 'Button', code, '', '', '', '',
                             '', '', '', '', '', '', 'FX: beat em grupo'])
    prefix = text if text.endswith(('\n', '\r')) else text + newline
    return (prefix + output.getvalue()).encode('utf-8'), True


def atomic_replace(path, content):
    fd, tmp = tempfile.mkstemp(prefix='.rev1-fx-', dir=str(path.parent))
    try:
        with os.fdopen(fd, 'wb') as output:
            output.write(content)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def main():
    if not base.EXE.is_file() or hashlib.sha256(base.EXE.read_bytes()).hexdigest() != base.EXPECTED_SHA256:
        raise RuntimeError('Executavel rekordbox diferente do build testado.')
    device = base.frida.get_local_device()
    if any(p.name.lower() == 'rekordbox.exe' for p in device.enumerate_processes()):
        raise RuntimeError('Feche o rekordbox antes de iniciar o perfil FX/CUE.')
    if not MAPPING.is_file():
        MAPPING.parent.mkdir(parents=True, exist_ok=True)
        with MAPPING.open('xb') as output:
            output.write((HERE / 'DDJ-REV1.midi.csv').read_bytes())
        base.log(f'Mapeamento pessoal inicial criado: {MAPPING}')
    before = MAPPING.read_bytes()
    after, changed = prepare_mapping(before)
    if changed:
        stamp = datetime.now().strftime('%Y%m%d-%H%M%S-%f')
        backup = MAPPING.with_name(f'DDJ-REV1.before-fx-cue-{stamp}.backup')
        with backup.open('xb') as output:
            output.write(before)
        atomic_replace(MAPPING, after)
        base.log(f'Mapeamento atualizado; backup: {backup}')
    state = (HERE / 'rev1_fx_cue_state.js').read_text(encoding='utf-8')
    hook = (HERE / 'rev1_fx_cue_hook.js').read_text(encoding='utf-8')
    base.SCRIPT = state + '\n' + base.SCRIPT + '\n' + hook
    try:
        base.main()
    except Exception:
        if changed and MAPPING.read_bytes() == after:
            atomic_replace(MAPPING, before)
            base.log('Falha ao iniciar: mapeamento anterior restaurado.')
        raise


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        base.log(f'ERRO perfil FX/CUE: {exc}')
        sys.exit(1)
