"""Verify the text-only release and its checksums without application files."""
from pathlib import Path
import hashlib
import subprocess
root = Path(__file__).resolve().parents[1]
tracked = subprocess.check_output(['git', 'ls-files', '-z'], cwd=root).decode().split('\0')
for name in filter(None, tracked):
    path = Path(name)
    assert path.parts[0] not in {'originals', 'work', '.vfzh', '__pycache__'}, name
    assert path.suffix.lower() not in {'.exe', '.dll', '.pyd', '.pyc', '.zip'}, name
    data = (root / path).read_bytes()
    assert b'\0' not in data, name
    data.decode('utf-8')
for line in (root / 'SHA256SUMS').read_text(encoding='utf-8').splitlines():
    expected, name = line.split('  ', 1)
    assert hashlib.sha256((root / name).read_bytes()).hexdigest() == expected, name
print('PASS: tracked source-only files and release checksums')
