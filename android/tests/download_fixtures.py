"""Download only pinned, SHA-verified catalog files for engineering tests."""
import hashlib
import json
import sys
import time
import urllib.request
from pathlib import Path

destination = Path(sys.argv[1])
destination.mkdir(parents=True, exist_ok=True)
catalog = json.loads((Path(__file__).resolve().parents[1] / 'app/src/main/assets/models.json').read_text())
for identifier in sys.argv[2:]:
    model = next(m for m in catalog if m['id'] == identifier)
    for index, data in enumerate(model['files']):
        target = destination / f'{identifier}-{index}.gguf'
        if not target.exists():
            partial = target.with_suffix('.partial')
            deadline = time.monotonic()+600
            for attempt in range(3):
                offset = partial.stat().st_size if partial.exists() else 0
                if offset == data['size']:
                    partial.replace(target)
                    break
                if offset > data['size']:
                    partial.unlink()
                    offset = 0
                request = urllib.request.Request(
                    data['url']+'?download=true&verify='+str(time.time_ns()),
                    headers={'Range': f'bytes={offset}-'} if offset else {})
                try:
                    with urllib.request.urlopen(request, timeout=45) as response:
                        resumed = offset and response.status == 206
                        if resumed:
                            assert response.headers['Content-Range'].startswith(f'bytes {offset}-')
                        else:
                            offset = 0
                        last_report = offset
                        with partial.open('ab' if resumed else 'wb') as out:
                            while chunk := response.read(1024 * 1024):
                                out.write(chunk)
                                offset += len(chunk)
                                if offset-last_report >= 256*1024*1024:
                                    print('DOWNLOAD', target.name, offset, '/', data['size'], flush=True)
                                    last_report = offset
                                if offset > data['size']:
                                    raise ValueError('Response exceeds pinned size')
                                if time.monotonic() > deadline:
                                    raise TimeoutError('Fixture download exceeded 10 minutes')
                    assert offset == data['size'], (target, offset, data['size'])
                    partial.replace(target)
                    break
                except Exception:
                    if attempt == 2 or time.monotonic() > deadline:
                        raise
                    print('RETRY', target.name, 'offset', offset, flush=True)
        digest = hashlib.sha256()
        with target.open('rb') as source:
            while chunk := source.read(8 * 1024 * 1024):
                digest.update(chunk)
        assert target.stat().st_size == data['size'], target
        assert digest.hexdigest() == data['sha256'], target
        print('VERIFIED', identifier, target.name, flush=True)
