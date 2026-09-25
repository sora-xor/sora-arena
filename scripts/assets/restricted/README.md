# Restricted asset manifests

One `<source>.json` per restricted source (Sonniss, Fab, Mixamo, CMU raw, ...). Plan section 2.4. No RST source has been approved yet (decisions D1 and D3, user steps U3 and U6).

The REF manifests here record files that are only looked at or listened to, never shipped, traced or sampled:

- `audio_wikimedia_reference.json`: a CC0 recording of an uncleared composition (written by `scripts/audio/fetch_cc0_audio.py`);
- `catbasev6-reference-photos.json`: CC BY 2.0 cat photographs, outside the plan allowlist (written by `scripts/art/fetch_cat_base_v6_sources.py`).

These manifests list hashes and paths, **never file contents**. The files live only in `Local/ThirdPartyRaw/<source>/` or `Content/ThirdPartyRestricted/<source>/`, both gitignored.

```json
{
  "schema_version": 2,
  "kind": "restricted-manifest",
  "source": "sonniss",
  "records": [
    {
      "asset_id": "sonniss-2026/hooves-dirt-01",
      "name": "Animal Footsteps Foley - Hooves, dirt 01",
      "tier": "RST",
      "license": "Sonniss GDC Game Audio Bundle License",
      "license_url": "https://sonniss.com/gdc-bundle-license/",
      "listing_url": "https://sonniss.com/gameaudiogdc",
      "entitlement_owner": "user (accepted 2026-..-.., step U6)",
      "user_step": "U6",
      "origin_url": "https://sonniss.com/gameaudiogdc",
      "mirror_url": null,
      "commercial_use": true,
      "redistribution": "no-standalone",
      "derivatives": true,
      "platform_restriction": null,
      "ai_terms": "no-training",
      "agent_handling": "allowed",
      "attribution_text": null,
      "changes": null,
      "license_snapshot": {"url": "...", "path": "Local/ThirdPartyRaw/_licenses/sonniss-....pdf", "sha256": "..."},
      "access": "direct",
      "acquired_at_utc": "...",
      "acquired_by": "user",
      "storage": "local-private",
      "used_by": ["/Game/Audio/..."],
      "fallback": "asset_id of the PUB/OWN substitute",
      "imported_packages": ["/Game/ThirdPartyRestricted/Sonniss/..."],
      "files": [
        {"path": "Local/ThirdPartyRaw/sonniss/....wav", "sha256": "...", "bytes": 0}
      ]
    }
  ]
}
```

`scripts/assets/check_restricted.py` verifies the local copies and prints the matching user step for anything missing. `scripts/assets/validate_asset_ledger.py` fails if any restricted path or content is tracked by git.
