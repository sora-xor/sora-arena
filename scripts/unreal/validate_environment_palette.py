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
roof_root=root/'GreyRoofTiles'
roof=json.loads((roof_root/'manifest.json').read_text())
assert roof['schema_version']==1 and roof['asset_id']=='grey_roof_tiles' and roof['role']=='kawara'
assert roof['asset_url']=='https://polyhaven.com/a/grey_roof_tiles'
assert roof['metadata_url']=='https://api.polyhaven.com/files/grey_roof_tiles'
assert roof['authors']=={'Rob Tuytel':'All'}
assert roof['license']=='CC0-1.0' and roof['license_url']=='https://polyhaven.com/license'
assert roof['source_dimensions_mm']==[3000,3000] and roof['tile_size_cm']==300.0
assert roof['resolution']=='4k'
assert roof['unreal_instance']=='/Game/Generated/Environment/MI_Nyaagyu_Kawara.MI_Nyaagyu_Kawara'
assert [item['channel'] for item in roof['files']]==['Diffuse','nor_dx','arm']
for item in roof['files']:
    filename='grey_roof_tiles_'+('diff' if item['channel']=='Diffuse' else item['channel'])+'_4k.'+item['format']
    assert item['file']==filename and item['format'] in ('jpg','png')
    assert item['url']==f'https://dl.polyhaven.org/file/ph-assets/Textures/{item["format"]}/4k/grey_roof_tiles/{filename}'
    data=(roof_root/filename).read_bytes()
    assert len(data)==item['bytes']
    assert hashlib.sha256(data).hexdigest()==item['sha256']
    assert hashlib.md5(data).hexdigest()==item['upstream_md5']
    if item['format']=='png':
        assert data[:8]==b'\x89PNG\r\n\x1a\n'
        assert struct.unpack('>II',data[16:24])==(4096,4096)
    else:
        assert data[:2]==b'\xff\xd8' and data[-2:]==b'\xff\xd9'
    total+=len(data);count+=1
assert count==16
print(f'Environment palette validated: 6 CC0 assets, {count} files, {total:,} bytes; hashes, upstream checksums, roles and PNG resolution verified.')
