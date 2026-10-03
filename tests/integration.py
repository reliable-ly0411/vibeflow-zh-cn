"""Real-version integration test against a COPY of user-provided original files."""
from pathlib import Path
import json
import shutil
import sys
import tempfile
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import patch

originals = Path(sys.argv[1]).resolve()  # Flat original files; never altered.
info = patch.manifest()
with tempfile.TemporaryDirectory(prefix='vfzh integration ') as directory:
    app = Path(directory) / 'original application'
    mirror = Path(directory) / 'render mirror'
    for item in info['files']:
        source = originals / item['payload']
        patch.require(source, item['original'])
        target = app / item['path']
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        if item['path'].startswith('bin/') and item['payload'].endswith(('.dll', '.exe')):
            target = mirror / item['path']
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
    personal = app / 'user-settings.json'
    personal.write_text('private settings preserved', encoding='utf-8')
    patch.check(app, mirror, info)
    patch.build(app, info)
    print(patch.install(app, mirror, info))
    print(patch.install(app, mirror, info))
    patch.verify_state(patch.read_state(app))
    print(patch.uninstall(app))
    patch.check(app, mirror, info)
    assert personal.read_text() == 'private settings preserved'
    print('PASS: clean build, expected hashes, install, repeat install, verify, byte-exact restore, preserved settings, retained backups.')
