"""Validate pinned downloads, hashes, sizes and the supported vision pair."""
import json
import re
from pathlib import Path
from urllib.parse import urlparse

models = json.loads((Path(__file__).parent / 'app/src/main/assets/models.json').read_text())
assert len(models) >= 31
mobile = [m for m in models if 3 <= m['parameters'] <= 6]
assert len(mobile) >= 10
assert sum(m['vision'] for m in mobile) >= 3
assert sum(m['kind'] == 'code' for m in mobile) >= 5
local_files = {}
assert sum(m['parameters'] >= 5 for m in models) > 10
assert len({m['id'] for m in models}) == len(models)
for model in models:
    assert re.fullmatch(r'[0-9a-f]{40}', model['revision'])
    assert model['kvElementsPerToken'] > 0
    assert model['architectureSource']
    assert model['parameters'] > 0
    assert model['kind'] in {'chat', 'code', 'reasoning', 'vision'}
    assert model['vision'] == (model['kind'] == 'vision')
    assert model['description'] and model['quant']
    assert len(model['files']) == (2 if model['vision'] else 1)
    for asset in model['files']:
        url = urlparse(asset['url'])
        assert url.scheme == 'https' and url.netloc == 'huggingface.co'
        assert '/resolve/' + model['revision'] + '/' in url.path
        assert asset['file'].endswith('.gguf') and '/' not in asset['file']
        assert re.fullmatch(r'[0-9a-f]{64}', asset['sha256'])
        assert asset['size'] > 1_000_000
        identity = (asset['sha256'], asset['size'])
        assert local_files.setdefault(asset['file'], identity) == identity, 'Conflicting local filenames'
    assert set(model.get('skills', [])) <= {'code', 'reasoning', 'chat', 'vision'}
print(f'{len(models)} pinned models validated')
