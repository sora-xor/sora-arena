"""Fetch the fixed Nyaagyu Estate CC0 production palette from official Poly Haven.

Powered by Poly Haven: https://polyhaven.com
Asset license: https://polyhaven.com/license
Current API terms: https://polyhaven.com/our-api (commercial use allowed July 2026).
Downloads actual production texture/HDR files, never website preview renders.
"""
from pathlib import Path
import concurrent.futures
import hashlib
import json
import urllib.request
from urllib.parse import urlparse
from datetime import datetime,timezone

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'Content/SourceArt/Environment/PolyHaven'
OUT.mkdir(parents=True,exist_ok=True)
AGENT='SORA-Arena-Asset-Authoring/0.1 (Powered by Poly Haven; offline game production)'
SELECTION=[('wood_planks_dirt','timber','4k'),('stone_floor','stone','2k'),('brown_mud_leaves_01','soil','2k'),('rusty_metal_02','metal','2k'),('kloofendal_overcast_puresky','sky','4k')]

def request(url):
    req=urllib.request.Request(url,headers={'User-Agent':AGENT})
    return urllib.request.urlopen(req,timeout=90)

def api(path):
    with request('https://api.polyhaven.com/'+path) as response:return json.load(response)

metadata=api('assets')
records=[];downloads=[]
for asset_id,role,resolution in SELECTION:
    info=metadata[asset_id];files=api('files/'+asset_id)
    record={'asset_id':asset_id,'name':info['name'],'role':role,'resolution':resolution,
      'asset_url':'https://polyhaven.com/a/'+asset_id,'metadata_url':'https://api.polyhaven.com/files/'+asset_id,
      'license':'CC0-1.0','license_url':'https://polyhaven.com/license','legal_code_url':'https://creativecommons.org/publicdomain/zero/1.0/legalcode',
      'authors':info.get('authors',{}),'source_dimensions_mm':info.get('dimensions'),
      'tile_size_cm':round(info.get('dimensions',[2000])[0]/10,4) if role!='sky' else None,'files':[]}
    roles=[('hdri','hdr')] if role=='sky' else [('Diffuse','jpg'),('nor_dx','png'),('arm','png')]
    for channel,extension in roles:
        item=files[channel][resolution][extension]
        url=item['url']
        if urlparse(url).hostname not in ('dl.polyhaven.org','dl.polyhaven.com'):
            raise RuntimeError('Unexpected production asset host: '+url)
        filename=Path(urlparse(url).path).name
        entry={'channel':channel,'url':url,'file':f'{asset_id}/{filename}','format':extension,
          'bytes':item['size'],'upstream_md5':item.get('md5'),'sha256':None}
        record['files'].append(entry);downloads.append(entry)
    records.append(record)

def download(entry):
    path=OUT/entry['file'];path.parent.mkdir(parents=True,exist_ok=True)
    valid=False
    if path.is_file():
        data=path.read_bytes();valid=len(data)==entry['bytes'] and (not entry['upstream_md5'] or hashlib.md5(data).hexdigest()==entry['upstream_md5'])
    if not valid:
        with request(entry['url']) as response:data=response.read()
        if len(data)!=entry['bytes']:raise RuntimeError('Incomplete asset: '+entry['url'])
        if entry['upstream_md5'] and hashlib.md5(data).hexdigest()!=entry['upstream_md5']:raise RuntimeError('Upstream checksum mismatch: '+entry['url'])
        pending=path.with_suffix(path.suffix+'.partial');pending.write_bytes(data);pending.replace(path)
    entry['sha256']=hashlib.sha256(data).hexdigest()
    print(f"Verified {entry['file']} ({len(data):,} bytes)",flush=True)

with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:list(pool.map(download,downloads))
manifest={'schema_version':1,'purpose':'Production PBR surface textures and image-based lighting for the Nyaagyu Estate',
 'credit':'Powered by Poly Haven — https://polyhaven.com','asset_license':'CC0-1.0',
 'license_verified_at_utc':datetime.now(timezone.utc).isoformat(),'license_url':'https://polyhaven.com/license',
 'api_terms_url':'https://polyhaven.com/our-api','assets':records}
(OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
(OUT/'NOTICE.txt').write_text('Powered by Poly Haven — https://polyhaven.com\n\nThese texture and HDRI assets are provided free under CC0 1.0 Universal.\nCommercial use and redistribution are allowed. They remain public-domain assets, not proprietary SORA artwork.\nAsset pages, creators, exact source files and SHA-256 checksums are recorded in manifest.json.\nLicense: https://polyhaven.com/license\nLegal code: https://creativecommons.org/publicdomain/zero/1.0/legalcode\n\nOnly actual production texture and HDRI files are included. Poly Haven logos, website preview renders and user avatars are not included.\n',encoding='utf-8')
print(f'PALETTE_READY: {len(records)} assets / {len(downloads)} production files / {sum(d["bytes"] for d in downloads):,} bytes')
