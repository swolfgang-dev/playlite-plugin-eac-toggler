"""Native Elden Ring launcher switching; never overwrite unrelated files."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile

STATE='.playlite-eac-toggler'
APPID=b'1245620\n'


def digest(path):
    result = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            result.update(chunk)
    return result.hexdigest()


def folder(directory):
    root=Path(directory).expanduser().resolve()
    if not (root/'eldenring.exe').is_file() and (root/'Game').is_dir():root=root/'Game'
    for path in (root/'eldenring.exe',root/'start_protected_game.exe',root/'steam_appid.txt',root/STATE):
        if path.is_symlink():raise ValueError('Refusing symlinked game or backup files.')
    for name in ('eldenring.exe','start_protected_game.exe'):
        path=root/name
        if not path.is_file():raise ValueError('Select an Elden Ring installation containing '+name+'.')
        with path.open('rb') as stream:
            if stream.read(2)!=b'MZ':raise ValueError(name+' is not a Windows executable.')
    return root


def replace(source,target):
    temporary=None
    try:
        with tempfile.NamedTemporaryFile(dir=target.parent,delete=False) as stream:
            temporary=Path(stream.name)
            with source.open('rb') as original:shutil.copyfileobj(original,stream)
            stream.flush();os.fsync(stream.fileno())
        shutil.copymode(source,temporary)
        temporary.replace(target)
    finally:
        if temporary and temporary.exists():temporary.unlink()


def state(root):
    marker=root/STATE/'state.json'
    if marker.is_symlink():raise ValueError('Refusing a symlinked backup record.')
    if not marker.is_file():raise ValueError('The backup is incomplete. Restore game files through Steam before retrying.')
    record=json.loads(marker.read_text())
    if (not isinstance(record, dict) or type(record.get('created_appid')) is not bool
            or any(not isinstance(record.get(key), str) or len(record[key]) != 64
                   or any(character not in '0123456789abcdef' for character in record[key])
                   for key in ('original', 'patched'))):
        raise ValueError('The backup record is invalid. No game files were changed.')
    original=root/STATE/'start_protected_game.exe'
    if original.is_symlink() or not original.is_file() or digest(original)!=record['original']:
        raise ValueError('The original launcher backup is missing or changed.')
    return record


def status(directory):
    root=folder(directory)
    if not (root/STATE).exists():return 'Enabled'
    record=state(root)
    current=digest(root/'start_protected_game.exe')
    if current==record['patched'] and digest(root/'eldenring.exe')==record['patched']:return 'Disabled'
    if current==record['original']:return 'Restore pending'
    return 'Game files changed'


def disable(directory):
    root=folder(directory);backup=root/STATE
    if backup.exists():raise ValueError('A backup already exists. Enable EAC before disabling it again.')
    if digest(root/'eldenring.exe')==digest(root/'start_protected_game.exe'):
        raise ValueError('The launcher is already replaced without a plugin backup. Verify game files in Steam first.')
    appid=root/'steam_appid.txt'
    if appid.exists() and (not appid.is_file() or appid.read_bytes().strip()!=b'1245620'):
        raise ValueError('An unrelated steam_appid.txt already exists.')
    backup.mkdir(mode=0o700)
    try:
        shutil.copy2(root/'start_protected_game.exe',backup/'start_protected_game.exe')
        shutil.copy2(root/'eldenring.exe',backup/'offline.exe')
        record={'original':digest(backup/'start_protected_game.exe'),'patched':digest(backup/'offline.exe'),'created_appid':not appid.exists()}
        (backup/'state.json').write_text(json.dumps(record))
        if record['created_appid']:
            with appid.open('xb') as stream:stream.write(APPID)
        replace(backup/'offline.exe',root/'start_protected_game.exe')
    except Exception:
        if (backup/'state.json').is_file():enable(root)
        else:shutil.rmtree(backup)
        raise


def enable(directory):
    root=folder(directory);backup=root/STATE;record=state(root)
    if digest(root/'start_protected_game.exe') not in (record['patched'],record['original']):
        raise ValueError('The launcher changed after EAC was disabled. No files were overwritten; verify game files in Steam.')
    appid=root/'steam_appid.txt'
    if record['created_appid'] and appid.exists() and appid.read_bytes()!=APPID:
        raise ValueError('steam_appid.txt changed after disabling EAC. No files were overwritten.')
    replace(backup/'start_protected_game.exe',root/'start_protected_game.exe')
    if record['created_appid'] and appid.exists():appid.unlink()
    shutil.rmtree(backup)
