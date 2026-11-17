"""Validate pinned downloads, hashes, sizes and the supported vision pair."""
import json
import re
from pathlib import Path
from urllib.parse import urlparse

models = json.loads((Path(__file__).parent / 'app/src/main/assets/models.json').read_text())
assert len({m['id'] for m in models}) == len(models)
for model in models:
    assert re.fullmatch(r'[0-9a-f]{40}', model['revision'])
    assert model['ram'] >= 2
    assert len(model['files']) == (2 if model['vision'] else 1)
    for asset in model['files']:
        url = urlparse(asset['url'])
        assert url.scheme == 'https' and url.netloc == 'huggingface.co'
        assert '/resolve/' + model['revision'] + '/' in url.path
        assert asset['file'].endswith('.gguf') and '/' not in asset['file']
        assert re.fullmatch(r'[0-9a-f]{64}', asset['sha256'])
        assert asset['size'] > 1_000_000
print(f'{len(models)} pinned models validated')
