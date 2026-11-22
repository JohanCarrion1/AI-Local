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
        digest = hashlib.sha256()
        if not target.exists():
            url = data['url'] + '?download=true&verify=' + str(time.time_ns())
            with urllib.request.urlopen(url, timeout=180) as response, target.open('wb') as out:
                while chunk := response.read(8 * 1024 * 1024):
                    out.write(chunk)
        with target.open('rb') as source:
            while chunk := source.read(8 * 1024 * 1024):
                digest.update(chunk)
        assert target.stat().st_size == data['size'], target
        assert digest.hexdigest() == data['sha256'], target
        print('VERIFIED', identifier, target.name, flush=True)
