import hashlib
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch as mock
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import patch


class TransactionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='vfzh test ')
        self.base = Path(self.temp.name)
        self.app = self.base / 'application with spaces'
        self.mirror = self.base / 'render mirror'
        self.payload = self.base / 'payload'
        self.payload.mkdir()
        self.files = []
        for name in ['one.dll', 'two.exe']:
            old, new = ('old ' + name).encode(), ('new ' + name).encode()
            for root in (self.app, self.mirror):
                (root / 'bin').mkdir(parents=True, exist_ok=True)
                (root / 'bin' / name).write_bytes(old)
            (self.payload / name).write_bytes(new)
            self.files.append(dict(payload=name, path='bin/' + name, original=hashlib.sha256(old).hexdigest(), patched=hashlib.sha256(new).hexdigest()))
        self.info = dict(files=self.files)
        (self.app / 'personal-settings.json').write_text('keep me')

    def tearDown(self):
        self.temp.cleanup()

    def install(self):
        return patch.install(self.app, self.mirror, self.info, self.payload)

    def originals(self):
        for item in patch.targets(self.app, self.mirror, self.info):
            patch.require(item['target'], item['original'])
        self.assertEqual((self.app / 'personal-settings.json').read_text(), 'keep me')

    def test_install_repeat_restore_and_backup_retention(self):
        self.install()
        state = patch.read_state(self.app)
        self.assertIn('Already installed', self.install())
        for item in state['files']:
            if item['link_to']:
                self.assertTrue(Path(item['target']).samefile(item['link_to']))
        patch.uninstall(self.app)
        self.originals()
        self.assertIn('Already restored', patch.uninstall(self.app))
        for item in state['files']:
            patch.require(item['backup'], item['original'])
        self.install()
        patch.uninstall(self.app)
        self.originals()

    def test_reject_unknown_input_before_backup_or_target_write(self):
        (self.app / 'bin/two.exe').write_bytes(b'changed')
        with self.assertRaises(RuntimeError):
            self.install()
        self.assertEqual((self.app / 'bin/one.dll').read_bytes(), b'old one.dll')
        self.assertFalse((self.app / '.vfzh/installation.json').exists())

    def test_reject_modified_output(self):
        self.install()
        (self.app / 'bin/two.exe').write_bytes(b'updated application')
        with self.assertRaises(RuntimeError):
            patch.uninstall(self.app)
        self.assertEqual((self.app / 'bin/two.exe').read_bytes(), b'updated application')

    def test_reject_damaged_backup(self):
        self.install()
        Path(patch.read_state(self.app)['files'][0]['backup']).write_bytes(b'bad')
        with self.assertRaises(RuntimeError):
            patch.uninstall(self.app)

    def test_write_failure_rolls_back(self):
        real = patch.atomic_copy
        calls = 0
        def fail_once(*args, **kwargs):
            nonlocal calls
            calls += 1
            if calls == 3:
                raise OSError('injected write failure')
            return real(*args, **kwargs)
        with mock('patch.atomic_copy', side_effect=fail_once):
            with self.assertRaises(OSError):
                self.install()
        self.originals()
        self.assertEqual(patch.read_state(self.app)['status'], 'rolled-back')

    def test_recover_interrupted_restore(self):
        self.install()
        state = patch.read_state(self.app)
        item = state['files'][0]
        patch.atomic_copy(item['backup'], item['target'])
        state['status'] = 'restoring'
        patch.save_state(self.app / '.vfzh/installation.json', state)
        patch.uninstall(self.app)
        self.originals()

    def test_exclusive_lock(self):
        with patch.lock(self.app):
            with self.assertRaises(RuntimeError):
                self.install()
        self.originals()


if __name__ == '__main__':
    unittest.main()
