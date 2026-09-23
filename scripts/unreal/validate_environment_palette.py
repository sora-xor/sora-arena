"""Check the exact production assets and their recorded rights before import."""
from pathlib import Path
from urllib.parse import urlparse
import hashlib
import json
import struct

root=Path(__file__).resolve().parents[2]/'Content/SourceArt/Environment/PolyHaven'
manifest=json.loads((root/'manifest.json').read_text())
assert manifest['schema_version']==1 and manifest['asset_license']=='CC0-1.0'
assert manifest['license_url']=='https://polyhaven.com/license'
assert {a['role'] for a in manifest['assets']}=={'timber','stone','soil','metal','sky'}
total=0;count=0
for asset in manifest['assets']:
    assert asset['license']=='CC0-1.0' and asset['authors']
    assert asset['asset_url']=='https://polyhaven.com/a/'+asset['asset_id']
    assert asset['resolution'] in ('2k','4k')
    assert {f['channel'] for f in asset['files']}==({'hdri'} if asset['role']=='sky' else {'Diffuse','nor_dx','arm'})
    if asset['role']!='sky':assert 50<=asset['tile_size_cm']<=1000
    for file in asset['files']:
        assert urlparse(file['url']).hostname in ('dl.polyhaven.org','dl.polyhaven.com')
        data=(root/file['file']).read_bytes()
        assert len(data)==file['bytes']
        assert hashlib.sha256(data).hexdigest()==file['sha256']
        assert hashlib.md5(data).hexdigest()==file['upstream_md5']
        if file['format']=='png':
            assert data[:8]==b'\x89PNG\r\n\x1a\n'
            size=int(asset['resolution'][:-1])*1024
            assert struct.unpack('>II',data[16:24])==(size,size)
        elif file['format']=='jpg':assert data[:2]==b'\xff\xd8' and data[-2:]==b'\xff\xd9'
        elif file['format']=='hdr':assert data.startswith((b'#?RADIANCE',b'#?RGBE'))
        else:raise AssertionError('Unapproved asset format')
        total+=len(data);count+=1
assert count==13
print(f'Environment palette validated: 5 CC0 assets, {count} files, {total:,} bytes; hashes, upstream checksums, roles and PNG resolution verified.')
