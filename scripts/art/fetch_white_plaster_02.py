"""Pin Poly Haven's CC0 White Plaster 02 maps for the Nyaagyu kura.

Run: python3 scripts/art/fetch_white_plaster_02.py
The fixed URLs, byte lengths, upstream MD5 values, and downloaded SHA-256
digests make this an auditable source acquisition, not an editor-time fetch.
"""

import hashlib
import json
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "Content/SourceArt/Environment/PolyHaven/WhitePlaster02"
OUT.mkdir(parents=True, exist_ok=True)
RECORDS = (
    ("Diffuse", "white_plaster_02_diff_2k.jpg", 2568315,
     "35f9c96c16aa0d934da7884b232f6d07"),
    ("nor_dx", "white_plaster_02_nor_dx_2k.png", 24664322,
     "3b0839a30985ec8ba67130ff52358283"),
    ("arm", "white_plaster_02_arm_2k.jpg", 894383,
     "8037fca09e797a6664834a00adbe05aa"),
)
files=[]
for channel,name,size,md5 in RECORDS:
    kind = "png" if name.endswith(".png") else "jpg"
    url=f"https://dl.polyhaven.org/file/ph-assets/Textures/{kind}/2k/white_plaster_02/{name}"
    destination=OUT/name
    if destination.is_file():
        data=destination.read_bytes()
    else:
        request=urllib.request.Request(url,headers={"User-Agent":"SoraArenaAssetAuthoring/0.1 (Powered by Poly Haven)"})
        with urllib.request.urlopen(request,timeout=90) as response:
            data=response.read()
        destination.write_bytes(data)
    assert len(data)==size,(name,"byte length changed")
    assert hashlib.md5(data).hexdigest()==md5,(name,"upstream content changed")
    files.append({"channel":channel,"file":name,"url":url,"format":kind,
                  "bytes":size,"upstream_md5":md5,
                  "sha256":hashlib.sha256(data).hexdigest()})
manifest={
    "schema_version":1,"asset_id":"white_plaster_02","name":"White Plaster 02",
    "role":"plaster","asset_url":"https://polyhaven.com/a/white_plaster_02",
    "metadata_url":"https://api.polyhaven.com/files/white_plaster_02",
    "info_url":"https://api.polyhaven.com/info/white_plaster_02",
    "authors":{"Rob Tuytel":"All"},"license":"CC0-1.0",
    "license_url":"https://polyhaven.com/license",
    "legal_code_url":"https://creativecommons.org/publicdomain/zero/1.0/legalcode",
    "resolution":"2k","source_dimensions_mm":[1000,1000],"tile_size_cm":100.0,
    "unreal_instance":"/Game/Generated/Environment/MI_Nyaagyu_Plaster.MI_Nyaagyu_Plaster",
    "application":"World-aligned smooth weathered plaster color, micro-normal, and AO/roughness/metallic on original project-authored kura walls. This is a surface scan, not a historical reconstruction.",
    "files":files,
}
(OUT/"manifest.json").write_text(json.dumps(manifest,indent=2)+"\n",encoding="utf-8")
(OUT/"NOTICE.txt").write_text(
    "Powered by Poly Haven — https://polyhaven.com\n\n"
    "White Plaster 02 by Rob Tuytel is provided under CC0 1.0 Universal.\n"
    "Commercial use and redistribution are allowed. Exact source files and\n"
    "SHA-256 checksums are recorded in manifest.json.\n"
    "License: https://polyhaven.com/license\n"
    "Legal code: https://creativecommons.org/publicdomain/zero/1.0/legalcode\n",
    encoding="utf-8")
print("NYAAGYU_WHITE_PLASTER_PINNED",[(f["channel"],f["bytes"]) for f in files])
