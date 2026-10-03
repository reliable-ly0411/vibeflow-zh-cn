#!/usr/bin/env python3
"""Build and install a version-pinned, source-only VibeFlow localization."""
import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parent


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def require(path, expected):
    if not Path(path).is_file() or digest(path) != expected:
        raise RuntimeError(f'Missing or incompatible file: {path}')


def manifest():
    return json.loads((ROOT / 'compatibility.json').read_text(encoding='utf-8'))


def targets(app, mirror, info):
    result = []
    for item in info['files']:
        target = app / item['path']
        result.append(dict(item, target=str(target), link_to=''))
        if mirror and item['path'].startswith('bin/') and item['payload'].endswith(('.dll', '.exe')):
            result.append(dict(item, target=str(mirror / item['path']), link_to=str(target)))
    return result


def closed(app, mirror):
    import psutil
    roots = [app / 'bin'] + ([mirror / 'bin'] if mirror else [])
    for process in psutil.process_iter(['pid', 'exe']):
        try:
            executable = process.info['exe']
            if executable and any(Path(executable).resolve().is_relative_to(p.resolve()) for p in roots):
                raise RuntimeError(f'Close VibeFlow and bundled tools first (PID {process.pid}). Use a separate Python installation for this tool.')
        except (psutil.NoSuchProcess, psutil.ZombieProcess):
            pass


def atomic_copy(source, target, link_to=''):
    target = Path(target)
    temporary = target.with_name(target.name + '.vfzh-' + uuid.uuid4().hex)
    try:
        if link_to:
            os.link(link_to, temporary)
        else:
            shutil.copy2(source, temporary)
        os.replace(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)


def save_state(path, state):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding='utf-8')
    os.replace(temporary, path)


@contextmanager
def lock(app):
    directory = app / '.vfzh'
    directory.mkdir(exist_ok=True)
    file = directory / 'operation.lock'
    try:
        fd = os.open(file, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        raise RuntimeError(f'Another operation or interrupted run holds {file}. Confirm no patch tool is running before removing this lock.')
    try:
        with os.fdopen(fd, 'w') as stream:
            stream.write(str(os.getpid()))
        yield
    finally:
        file.unlink(missing_ok=True)


def read_state(app):
    path = app / '.vfzh' / 'installation.json'
    if not path.exists():
        return None
    state = json.loads(path.read_text(encoding='utf-8'))
    if state['app'] != str(app):
        raise RuntimeError('Backup belongs to a different application path.')
    return state


def verify_state(state, restored=False):
    for item in state['files']:
        require(item['backup'], item['original'])
        require(item['target'], item['original'] if restored else item['patched'])


def check(app, mirror, info):
    state = read_state(app)
    if state and state['status'] == 'installed':
        verify_state(state)
        return 'already installed'
    for item in targets(app, mirror, info):
        require(item['target'], item['original'])
    return 'supported original installation'


def build(app, info):
    # Validate every source before creating or replacing any local build output.
    for item in info['files']:
        require(app / item['path'], item['original'])
    (ROOT / 'originals').mkdir(exist_ok=True)
    (ROOT / 'work').mkdir(exist_ok=True)
    for item in info['files']:
        shutil.copy2(app / item['path'], ROOT / 'originals' / item['payload'])
    env = dict(os.environ, PYTHONUTF8='1')
    for script in ['extract_qt_calls.py', 'extract_vtk_xml.py', 'build_patch.py', 'build_web.py', 'build_xml.py', 'verify_patch.py', 'verify_v2.py']:
        subprocess.run([sys.executable, str(ROOT / script)], check=True, env=env, cwd=ROOT)
    for item in info['files']:
        require(ROOT / 'work' / item['payload'], item['patched'])
    print('All 15 generated files match the tested version-2 SHA-256 values.')


def install(app, mirror, info, payload=None):
    payload = payload or ROOT / 'work'
    with lock(app):
        prior = read_state(app)
        if prior and prior['status'] == 'installed':
            verify_state(prior)
            return 'Already installed and verified.'
        if prior and prior['status'] not in ('restored', 'rolled-back'):
            raise RuntimeError('Interrupted installation: run uninstall to recover first.')
        records = targets(app, mirror, info)
        for item in records:
            require(item['target'], item['original'])
            require(payload / item['payload'], item['patched'])
        backup = app / '.vfzh' / ('backup-' + time.strftime('%Y%m%d-%H%M%S') + '-' + uuid.uuid4().hex[:8])
        backup.mkdir()
        for index, item in enumerate(records):
            item['backup'] = str(backup / (str(index) + '-' + item['payload']))
            shutil.copy2(item['target'], item['backup'])
            require(item['backup'], item['original'])
        state_path = app / '.vfzh' / 'installation.json'
        if prior:
            shutil.copy2(state_path, backup / 'previous-installation.json')
        state = dict(app=str(app), mirror=str(mirror) if mirror else '', status='backed-up', files=records)
        save_state(state_path, state)
        try:
            for item in records:
                atomic_copy(payload / item['payload'], item['target'], item['link_to'])
                require(item['target'], item['patched'])
            state['status'] = 'installed'
            save_state(state_path, state)
        except BaseException:
            for item in records:
                atomic_copy(item['backup'], item['target'], item['link_to'])
                require(item['target'], item['original'])
            state['status'] = 'rolled-back'
            save_state(state_path, state)
            raise
        verify_state(state)
        return f'Installed and verified {len(records)} paths. Backup: {backup}'


def uninstall(app):
    with lock(app):
        state = read_state(app)
        if not state:
            raise RuntimeError('No installation record. Nothing will be overwritten.')
        if state['status'] in ('restored', 'rolled-back'):
            verify_state(state, restored=True)
            return 'Already restored and verified.'
        # Recover an interrupted install/uninstall, but never overwrite unknown edits.
        for item in state['files']:
            require(item['backup'], item['original'])
            if digest(item['target']) not in (item['patched'], item['original']):
                raise RuntimeError(f"File changed after patching: {item['target']}")
        state['status'] = 'restoring'
        save_state(app / '.vfzh' / 'installation.json', state)
        for item in state['files']:
            atomic_copy(item['backup'], item['target'], item['link_to'])
            require(item['target'], item['original'])
        state['status'] = 'restored'
        save_state(app / '.vfzh' / 'installation.json', state)
        verify_state(state, restored=True)
        return 'Original bytes restored; backups retained.'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['check', 'build', 'install', 'verify', 'uninstall'])
    parser.add_argument('--app', required=True, type=Path, help='VibeFlow directory containing bin, resources and share')
    parser.add_argument('--mirror', type=Path, help='Optional existing rendering mirror directory containing bin')
    args = parser.parse_args()
    app = args.app.resolve()
    mirror = args.mirror.resolve() if args.mirror else None
    if not app.is_dir() or mirror == app:
        parser.error('Application directory must exist and mirror must be different.')
    if not __debug__:
        parser.error('Do not run this tool with Python optimization (-O).')
    info = manifest()
    if args.command in ('install', 'uninstall'):
        state = read_state(app)
        closed(app, Path(state['mirror']) if state and state['mirror'] else mirror)
    if args.command == 'check':
        print(check(app, mirror, info))
    elif args.command == 'build':
        build(app, info)
    elif args.command == 'install':
        print(install(app, mirror, info))
    elif args.command == 'uninstall':
        print(uninstall(app))
    else:
        state = read_state(app)
        if not state:
            raise RuntimeError('No installation record.')
        verify_state(state, restored=state['status'] in ('restored', 'rolled-back'))
        if state['status'] not in ('installed', 'restored', 'rolled-back'):
            raise RuntimeError('Interrupted operation; run uninstall to recover.')
        print('Verified all target files and backups; status=' + state['status'])


if __name__ == '__main__':
    try:
        main()
    except (RuntimeError, OSError, subprocess.CalledProcessError) as error:
        sys.exit(str(error))
