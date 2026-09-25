#!/usr/bin/env python3
"""Build Content/SourceArt/Audio/cues.proposed.json: the machine-readable audio cue proposal.

Every cue maps a gameplay event (USoraGameEvents delegates in Source/SoraArena/Public/SoraGameEvents.h, or an
animation / environment / UI trigger) to:
  * `files`       project-owned renders (tier OWN) under Content/SourceArt/Audio, verified to exist, and
  * `layers_cc0`  CC0 source layers in Local/ThirdPartyRaw/audio, verified against the SHA-256 ledger
                  manifests in scripts/assets/manifests/audio_*.json (import them into /Game before use).
Status values: ready-own | needs-assembly (OWN + CC0 layers to combine in a MetaSound) | layers-cc0
(CC0 layers only; placeholder unless the layer is good enough) | needed | blocked (a named dependency).

The engineering lane moves the approved result into Content/Data (this script never writes there).

  python3 scripts/audio/build_cue_proposal.py
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'Content/SourceArt/Audio/cues.proposed.json'
MANIFESTS = ROOT / 'scripts/assets/manifests'
AUDIO = 'Content/SourceArt/Audio'

_ledger: dict[str, dict] = {}
for mpath in sorted(MANIFESTS.glob('audio_*.json')):
    data = json.loads(mpath.read_text())
    for asset in data.get('assets', []):
        rows = list(asset.get('files', [])) + list(asset.get('downloads', []))
        if 'archive' in asset:
            rows.append(asset['archive'])
        _ledger[asset['asset_id']] = {'manifest': str(mpath.relative_to(ROOT)), 'rows': rows,
                                      'license': asset.get('license'), 'tier': asset.get('tier'),
                                      'use_policy': asset.get('use_policy', 'sample'),
                                      'placeholder_only': asset.get('placeholder_only', False)}
ERRORS: list[str] = []


def own(*patterns: str) -> list[str]:
    out = []
    for pat in patterns:
        hits = sorted(str(p.relative_to(ROOT)) for p in ROOT.glob(f'{AUDIO}/{pat}'))
        if not hits:
            ERRORS.append(f'no OWN file matches {pat}')
        out += hits
    return out


def cc0(asset_id: str, *needles: str, limit: int | None = None) -> dict:
    rec = _ledger.get(asset_id)
    if rec is None:
        ERRORS.append(f'asset not in ledger: {asset_id}')
        return {'asset_id': asset_id, 'files': []}
    if rec['use_policy'] != 'sample':
        ERRORS.append(f'{asset_id} is {rec["use_policy"]!r}; it may not be used as a layer')
    audio_ext = ('.wav', '.ogg', '.oga', '.flac', '.mp3', '.aif', '.aiff')
    files = []
    for row in rec['rows']:
        f = row['file']
        if not f.lower().endswith(audio_ext):
            continue
        if needles and not any(n.lower() in Path(f).name.lower() for n in needles):
            continue
        if not (ROOT / f).is_file():
            ERRORS.append(f'ledger file missing on disk: {f}')
        files.append({'file': f, 'sha256': row.get('sha256')})
    if not files:
        ERRORS.append(f'no files in {asset_id} match {needles}')
    if limit:
        files = files[:limit]
    return {'asset_id': asset_id, 'manifest': rec['manifest'], 'license': rec['license'], 'tier': rec['tier'],
            'placeholder_only': rec['placeholder_only'], 'files': files}


CUES: list[dict] = []


def cue(cid: str, trigger: str, bus: str, *, match: dict | None = None, files: list | None = None,
        layers: list | None = None, status: str | None = None, spatial: bool = True, attenuation: str | None = None,
        loop: bool = False, max_instances: int = 4, pitch_cents: tuple = (-40, 40), volume_db: tuple = (-1.5, 0.0),
        random: str = 'shuffle_no_repeat', caption: dict | None = None, notes: str = ''):
    files = files or []
    layers = layers or []
    if status is None:
        status = 'ready-own' if files and not layers else ('needs-assembly' if files else ('layers-cc0' if layers else 'needed'))
    CUES.append({'id': cid, 'trigger': trigger, 'match': match or {}, 'bus': bus, 'status': status,
                 'files': files, 'layers_cc0': layers, 'spatial': spatial,
                 'attenuation': attenuation or ('none' if not spatial else 'default'), 'loop': loop,
                 'max_instances': max_instances, 'random': random, 'pitch_cents': list(pitch_cents),
                 'volume_db': list(volume_db), 'caption': caption, 'notes': notes})


FFL = 'opengameart/the-free-firearm-sound-library'
MED_I = 'opengameart/medieval-sound-effects-weapon-impacts'
MED_T = 'opengameart/medieval-sound-effects-weapon-textures'
K_IMP = 'kenney/impact-sounds'


def build() -> dict:
    # ---------------- ranged weapons: OnWeaponFired (match WeaponId, catalog.json) ----------------
    cue('weapon.fired.arc_carbine', 'OnWeaponFired', 'SFX_Weapons', match={'WeaponId': 1},
        files=own('Original/Weapons/wpn_arc_carbine_fire_*.wav'), attenuation='weapon_long', max_instances=6)
    cue('weapon.fired.needle_smg', 'OnWeaponFired', 'SFX_Weapons', match={'WeaponId': 3},
        files=own('Original/Weapons/wpn_needle_smg_fire_*.wav'), attenuation='weapon_long', max_instances=8)
    cue('weapon.fired.phantom_smg', 'OnWeaponFired', 'SFX_Weapons', match={'WeaponId': 13},
        files=own('Original/Weapons/wpn_needle_smg_fire_*.wav'), attenuation='weapon_mid', max_instances=8,
        pitch_cents=(-250, -150), notes='Special sidegrade: same source, MetaSound pitch -2 st, 3 kHz low-pass and a '
        'short reverse pre-echo so it reads as "phantom". Replace with a bespoke render if playtests confuse it.')
    cue('weapon.fired.coil_matchlock', 'OnWeaponFired', 'SFX_Weapons', match={'WeaponId': 5},
        files=own('Original/Weapons/wpn_coil_matchlock_whine.wav'),
        layers=[cc0('opengameart/flare-ignition'), cc0(FFL, 'E_', limit=2), cc0(FFL, 'M_', limit=2)],
        attenuation='weapon_long', notes='Order: coil whine (0-0.9 s) -> pan flash (flare ignition, pitched down) '
        '-> ~40 ms -> report built from the Arisaka (E_*) and Mosin-Nagant (M_*) bolt-action recordings, low-passed '
        '7 kHz, plus a long outdoor tail. Black powder has more low-mid bloom and less crack than smokeless.')
    cue('weapon.fired.repeater', 'OnWeaponFired', 'SFX_Weapons', match={'WeaponId': 9},
        layers=[cc0(FFL, 'L_', limit=2), cc0(FFL, 'I_', limit=2)], attenuation='weapon_long',
        notes='Model 1894 (L_*) and Marlin 336 (I_*) lever-action reports: mechanical repeater identity.')
    cue('weapon.fired.pulse_carbine', 'OnWeaponFired', 'SFX_Weapons', match={'WeaponId': 11},
        files=own('Original/Weapons/wpn_pulse_carbine_fire_*.wav'), attenuation='weapon_long', max_instances=6)
    cue('weapon.charge.plasma_matchlock', 'OnWeaponFired (charge start, Kind=Hitscan, WeaponId 14)', 'SFX_Weapons',
        match={'WeaponId': 14, 'phase': 'charge'},
        files=own('Original/Weapons/wpn_plasma_matchlock_charge.wav'), attenuation='weapon_mid', max_instances=2,
        pitch_cents=(0, 0), notes='The full-charge lock click lands at 1.55 s; keep the charge time in the kernel '
                                  'and the file in sync (re-render if balance changes the charge).')
    cue('weapon.hold.plasma_matchlock', 'charged and held', 'SFX_Weapons', match={'WeaponId': 14, 'phase': 'hold'},
        files=own('Original/Weapons/wpn_plasma_matchlock_hold_loop.wav'), loop=True, attenuation='weapon_mid',
        max_instances=2, pitch_cents=(0, 0))
    cue('weapon.fired.plasma_matchlock', 'OnWeaponFired', 'SFX_Weapons', match={'WeaponId': 14},
        files=own('Original/Weapons/wpn_plasma_matchlock_fire_*.wav'), attenuation='weapon_long', max_instances=4)
    cue('weapon.fired.shock_emitter', 'OnWeaponFired (Kind=Beam, WeaponId 16)', 'SFX_Weapons', match={'WeaponId': 16},
        files=own('Original/Weapons/wpn_shock_emitter_start.wav', 'Original/Weapons/wpn_shock_emitter_loop.wav',
                  'Original/Weapons/wpn_shock_emitter_stop.wav'), attenuation='weapon_mid', max_instances=3,
        notes='start -> loop while firing -> stop (MetaSound with a trigger-on-release).')
    cue('weapon.fired.grenade_launcher', 'OnWeaponFired', 'SFX_Weapons', match={'WeaponId': 7},
        layers=[cc0('opengameart/cannon-fire'), cc0('opengameart/25-cc0-bang-firework-sfx', 'shot_')],
        attenuation='weapon_long', notes='Launch "thoonk": cannon layer pitched up, short; needs an original tube '
                                         'resonance layer before shipping.')
    cue('weapon.fired.micro_mortar', 'OnWeaponFired', 'SFX_Weapons', match={'WeaponId': 15},
        layers=[cc0('opengameart/25-cc0-bang-firework-sfx', 'cannon_')], attenuation='weapon_long')
    cue('weapon.fired.healing_lance', 'OnWeaponFired', 'SFX_Weapons', match={'WeaponId': 17},
        files=own('Original/Shields/shd_barrier_regen.wav'), status='needed', attenuation='weapon_mid',
        notes='Placeholder only (shield regen). Needs a warm, clearly non-hostile heal voice (League palette: '
              'bell / breath, never the cold alien glass).')
    cue('weapon.yumi.draw', 'yumi draw start (input / anim notify)', 'SFX_Weapons', match={'WeaponId': 18},
        layers=[cc0(MED_T, 'English Longbow Draw'), cc0(MED_T, 'Scythian Recurve Draw')], attenuation='foley_short')
    cue('weapon.yumi.nock', 'arrow nocked (hayago / quiver)', 'SFX_Weapons', match={'WeaponId': 18},
        layers=[cc0(MED_T, 'Nock Arrow'), cc0(MED_T, 'Set Arrow')], attenuation='foley_short')
    cue('weapon.fired.yumi', 'OnWeaponFired (Kind=Arrow)', 'SFX_Weapons', match={'WeaponId': 18},
        layers=[cc0(MED_T, 'English Longbow Shoot'), cc0(MED_T, 'Scythian Recurve Shoot')], attenuation='weapon_mid',
        notes='The yumi\'s tsurune (string ring) and yugaeri (bow rotation) are missing: record our own (plan §3.11 '
              'item 19) or use Freesound CC BY after the U2 login; longbow/recurve are stand-ins.')
    cue('projectile.arrow.flyby', 'arrow passes the listener (Kind=Arrow)', 'SFX_Weapons', match={'Kind': 'Arrow'},
        layers=[cc0(MED_T, 'Arrow Passby'), cc0(MED_T, 'Arrow Approach'), cc0(MED_T, 'Arrow Pass')],
        attenuation='flyby')
    cue('projectile.beam', 'OnWeaponFired (Kind=Beam) / boss beam', 'SFX_Weapons', match={'Kind': 'Beam'},
        files=own('Original/Weapons/wpn_energy_beam_start.wav', 'Original/Weapons/wpn_energy_beam_loop.wav',
                  'Original/Weapons/wpn_energy_beam_stop.wav'), attenuation='weapon_long', max_instances=3)
    cue('weapon.reload.cell_eject', 'reload window opens (energy weapons)', 'SFX_Weapons',
        files=own('Original/Weapons/wpn_cell_eject_*.wav'), attenuation='foley_short',
        caption={'ja': '［排莢音］', 'en': '[cell ejects]'}, notes='Also the Collatera reload-window telegraph.')

    # ---------------- melee: OnMeleeCommitted / OnStrikeResolved / OnGuarded / OnParried ----------------
    for wid, name in [(0, 'katana'), (4, 'wakizashi'), (10, 'tanto')]:
        cue(f'melee.committed.{name}', 'OnMeleeCommitted', 'SFX_Melee', match={'WeaponId': wid, 'WindupSeconds': '<0.5'},
            files=own('Original/Melee/mel_whoosh_katana_light_*.wav'), layers=[cc0(MED_T, 'Katana Swing')],
            attenuation='melee_close', pitch_cents=(-60, 60) if wid == 0 else (40, 160))
        cue(f'melee.committed.{name}.heavy', 'OnMeleeCommitted', 'SFX_Melee',
            match={'WeaponId': wid, 'WindupSeconds': '>=0.5'},
            files=own('Original/Melee/mel_whoosh_katana_heavy_*.wav'), attenuation='melee_close')
    cue('melee.committed.naginata', 'OnMeleeCommitted', 'SFX_Melee', match={'WeaponId': [12, 20]},
        files=own('Original/Melee/mel_whoosh_naginata_sweep_*.wav'), attenuation='melee_close')
    cue('melee.committed.yari', 'OnMeleeCommitted', 'SFX_Melee', match={'WeaponId': 19},
        files=own('Original/Melee/mel_whoosh_yari_thrust_*.wav'), layers=[cc0(MED_T, 'Spear Swing')],
        attenuation='melee_close')
    cue('melee.committed.kusarigama', 'OnMeleeCommitted', 'SFX_Melee', match={'WeaponId': 2},
        files=own('Original/Melee/mel_whoosh_kusarigama_chain_*.wav'),
        layers=[cc0('opengameart/chain-winch-sounds', limit=3)], attenuation='melee_close')
    cue('melee.committed.kanabo', 'OnMeleeCommitted', 'SFX_Melee', match={'WeaponId': [6, 8]},
        files=own('Original/Melee/mel_whoosh_kanabo_*.wav'), attenuation='melee_close',
        notes='Forge Hammer (8) shares the club whoosh; its hits use the workshop hammering layers.')
    cue('melee.committed.bokuto', 'OnMeleeCommitted (dojo, bokuto)', 'SFX_Melee', match={'dojo_weapon': 'bokuto'},
        files=own('Original/Melee/mel_whoosh_bokuto_*.wav'), attenuation='melee_close')
    cue('melee.committed.fukuro_shinai', 'OnMeleeCommitted (dojo, fukuro-shinai)', 'SFX_Melee',
        match={'dojo_weapon': 'fukuro_shinai'}, files=own('Original/Melee/mel_whoosh_fukuro_shinai_*.wav'),
        attenuation='melee_close')
    cue('melee.strike.hit_body', 'OnStrikeResolved (bHit)', 'SFX_Melee', match={'bHit': True},
        layers=[cc0(K_IMP, 'impactPunch_heavy'), cc0(K_IMP, 'impactSoft_heavy')], status='needed',
        attenuation='melee_close', notes='Placeholder (Kenney, stylised). Needs our own cloth / armour / cut foley '
        'sessions (lacquer plates, silk lacing, leather) — no photoreal CC0 source found.')
    cue('melee.guard', 'OnGuarded', 'SFX_Melee', files=own('Original/Melee/mel_guard_block_*.wav'),
        layers=[cc0(MED_I, 'Katana Blade on Blade'), cc0(MED_I, 'Hilt on Blade')], attenuation='melee_close')
    cue('melee.parry', 'OnParried', 'SFX_Melee',
        files=own('Original/Melee/mel_parry_full_light_*.wav', 'Original/Melee/mel_parry_full_heavy_*.wav'),
        layers=[cc0(MED_I, 'Katana Blade on Blade'), cc0(MED_I, 'Norse Sword Katana')], attenuation='melee_close',
        notes='Heavy variant when the parried attack was a committed heavy; add mel_parry_layer_sparks_* for awase.')
    cue('melee.parry.layers', 'OnParried (MetaSound layers)', 'SFX_Melee',
        files=own('Original/Melee/mel_parry_layer_*.wav'), attenuation='melee_close')
    cue('melee.dojo.clack', 'OnGuarded / OnParried / OnStrikeResolved with bDojo', 'SFX_Melee', match={'bDojo': True},
        files=own('Original/Melee/mel_bokuto_clack_*.wav'),
        layers=[cc0('opengameart/35-wooden-crackshitsdestructions', 'impactwood')], attenuation='melee_close')
    cue('melee.katana.draw', 'equip katana (nukitsuke)', 'SFX_Foley', layers=[cc0(MED_T, 'Katana Draw')],
        attenuation='foley_short')
    cue('melee.katana.sheathe', 'unequip katana / noto', 'SFX_Foley', layers=[cc0(MED_T, 'Katana Sheath')],
        attenuation='foley_short', notes='The noto "click" of the habaki seating needs a close foley layer.')

    # ---------------- damage, death, explosions ----------------
    cue('player.damaged', 'OnDamaged (Victim = local player)', 'SFX_Impacts',
        files=own('Original/Melee/mel_parry_layer_body_*.wav'), layers=[cc0(K_IMP, 'impactPunch_medium')],
        status='needs-assembly', spatial=False, notes='Low thump + short tinnitus-free muffle (SFX bus low-pass 1.5 s '
        'at < 25% health). Pain efforts are VO (blocked on B6).')
    cue('player.died', 'OnDied (Victim = local player, not sparring)', 'Music',
        files=own('Music/Stingers/mus_sting_player_death.wav'), spatial=False, max_instances=1, pitch_cents=(0, 0))
    cue('enemy.died', 'OnDied (Victim != local player)', 'SFX_Impacts', status='needed', attenuation='melee_close',
        notes='Body fall on wood / earth / stone and armour rattle; needs own foley.')
    cue('sparring.point', 'OnDied (bSparring) / dojo point', 'UI', files=own('Music/Stingers/mus_sting_duel_point.wav'),
        spatial=False, pitch_cents=(0, 0))
    cue('explosion.detonated', 'OnDetonated', 'SFX_Explosions',
        layers=[cc0('opengameart/25-cc0-bang-firework-sfx', 'bang_'), cc0('opengameart/muffled-distant-explosion'),
                cc0('opengameart/cannon-fire')], attenuation='explosion', max_instances=4,
        notes='Scale layers by Radius / Damage: close crack + body (bang_*), distant tail (muffled), '
              'sub drop synthesised in the MetaSound. Needs a debris layer (wood / tile) for the Edo spaces.')

    # ---------------- boss telegraphs and phases: OnBossPhase ----------------
    cue('boss.arrived', 'OnBossPhase (Arrived)', 'Music', files=own('Music/Stingers/mus_sting_boss_phase.wav'),
        spatial=False, max_instances=1, pitch_cents=(0, 0))
    cue('boss.windup.beam', 'OnBossPhase (Windup, bBeam)', 'SFX_Telegraph',
        files=own('Original/Telegraphs/tel_lock_cyan_900ms.wav'), pitch_cents=(0, 0), random='sequential',
        caption={'ja': '［照準固定音］', 'en': '[targeting lock]'},
        notes='Audible at Music 0; never ducked; the strike lands 900 ms after file start (Normal). Easy +30 % / '
              'Hard -15 %: time-stretch in the MetaSound, do not pitch.')
    cue('boss.windup.cleave', 'OnBossPhase (Windup, !bBeam)', 'SFX_Telegraph',
        files=own('Original/Telegraphs/tel_cleave_amber_01.wav'), pitch_cents=(0, 0),
        caption={'ja': '［大振りの予兆］', 'en': '[heavy swing winding up]'})
    cue('boss.windup.area_1500', 'OnBossPhase (Windup, 1500 ms area: seizure tiles / orbital strike)',
        'SFX_Telegraph', files=own('Original/Telegraphs/tel_cleave_amber_02.wav',
                                   'Original/Telegraphs/tel_margin_call_riser_1500ms.wav'), pitch_cents=(0, 0),
        caption={'ja': '［追証の警告音］', 'en': '[margin call rising]'})
    cue('boss.strike.beam', 'OnBossPhase (Strike, bBeam)', 'SFX_Weapons',
        files=own('Original/Weapons/wpn_energy_beam_start.wav', 'Original/Weapons/wpn_energy_beam_loop.wav'),
        attenuation='weapon_long')
    cue('boss.strike.cleave', 'OnBossPhase (Strike, !bBeam)', 'SFX_Melee',
        files=own('Original/Melee/mel_whoosh_kanabo_*.wav', 'Original/Melee/mel_parry_layer_body_*.wav'),
        attenuation='melee_close')
    cue('boss.defeated', 'OnBossPhase (Defeated)', 'Music', files=own('Music/Stingers/mus_sting_boss_phase.wav'),
        status='needed', spatial=False, notes='Placeholder: needs a bespoke release sting per boss (catharsis, '
                                              'League motif).')
    cue('boss.shield.hit', 'Collatera / drone shield absorbs damage', 'SFX_Impacts',
        files=own('Original/Shields/shd_barrier_hit_*.wav'), attenuation='weapon_mid')
    cue('boss.shield.break', 'shield broken', 'SFX_Impacts', files=own('Original/Shields/shd_barrier_break_*.wav'),
        attenuation='weapon_long', caption={'ja': '［障壁が砕ける］', 'en': '[barrier shatters]'})
    cue('boss.shield.regen', 'shield regeneration starts (4 s without damage)', 'SFX_Telegraph',
        files=own('Original/Shields/shd_barrier_regen.wav'), caption={'ja': '［障壁の再生］', 'en': '[barrier recharging]'})
    cue('barrier.hum', 'barrier / shield present', 'SFX_Alien', files=own('Original/Shields/shd_barrier_hum_loop.wav'),
        loop=True, attenuation='ambient_emitter', pitch_cents=(0, 0))

    # ---------------- campaign progression ----------------
    cue('chapter.started', 'OnChapterStarted', 'Music', files=own('Music/Stingers/mus_sting_chapter_start.wav'),
        spatial=False, max_instances=1, pitch_cents=(0, 0), notes='Title card: the vermillion seal lands on the '
                                                                  'odaiko + gong hit at 1.0 s.')
    cue('chapter.completed', 'OnChapterCompleted', 'Music', files=own('Music/Stingers/mus_sting_chapter_complete.wav'),
        spatial=False, max_instances=1, pitch_cents=(0, 0))
    cue('site.restored', 'OnSiteRestored', 'UI', files=own('Music/Stingers/mus_sting_site_restored.wav',
                                                         'Original/UI/ui_xor_credit_soroban_*.wav'),
        spatial=False, pitch_cents=(0, 0), notes='Stinger on the Music bus + soroban/rin on UI when the registry '
                                                 'entry is written.')

    # ---------------- footsteps (anim notify + physical material) ----------------
    cue('foot.wood', 'footstep on hinoki / engawa boards', 'SFX_Foley', files=own('Original/Foley/fol_board_creak_*.wav'),
        layers=[cc0(K_IMP, 'footstep_wood')], status='layers-cc0', attenuation='foley_short', max_instances=6,
        notes='Kenney steps are placeholder; board creak (OWN) is a quiet stealth layer. Needs own suri-ashi foley.')
    cue('foot.tatami', 'footstep on tatami', 'SFX_Foley', layers=[cc0(K_IMP, 'footstep_carpet')], status='needed',
        attenuation='foley_short', notes='Placeholder only.')
    cue('foot.earth', 'footstep on packed earth / sand', 'SFX_Foley',
        layers=[cc0('opengameart/fantozzis-footsteps-grasssand-stone', 'Sand')], attenuation='foley_short', max_instances=6)
    cue('foot.stone', 'footstep on stone / ishigaki / flagstones', 'SFX_Foley',
        layers=[cc0('opengameart/fantozzis-footsteps-grasssand-stone', 'Stone')], attenuation='foley_short', max_instances=6)
    cue('foot.grass', 'footstep on grass', 'SFX_Foley', layers=[cc0(K_IMP, 'footstep_grass')],
        attenuation='foley_short', max_instances=6, notes='Placeholder.')
    cue('foot.water', 'footstep in paddy / puddle / shallow water', 'SFX_Foley',
        layers=[cc0('opengameart/6-short-water-splashes')], attenuation='foley_short', max_instances=6,
        notes='Stealth noise class "puddle" (loud).')
    cue('foot.gravel', 'footstep on gravel', 'SFX_Foley', status='needed', attenuation='foley_short',
        notes='Gravel is a stealth noise surface; needs own recording (plan: Freesound CC0 after U2).')
    cue('foot.nightingale_floor', 'footstep on uguisubari (ch06)', 'SFX_Foley',
        files=own('Original/Foley/fol_nightingale_floor_*.wav'), attenuation='stealth_noise', max_instances=4,
        caption={'ja': '［鶯張りが鳴る］', 'en': '[nightingale floor chirps]'},
        notes='Silent on the edge-walk strip. Deliberately unlike real birdsong.')
    cue('foot.metal_grating', 'footstep on ship gantry grating (ch07)', 'SFX_Foley', status='needed',
        attenuation='foley_short')

    # ---------------- horse ----------------
    cue('horse.trot', 'Kurimaru / pack horse at trot', 'SFX_Foley', layers=[cc0('opengameart/horse-trotting')],
        status='blocked', attenuation='foley_mid', notes='Placeholder (jacket-on-bottle foley). Unshod hooves on '
        'earth / wood, snorts, bit and abumi jingle: blocked on the Freesound login (U2) or our own recordings.')
    for gait in ('walk', 'gallop', 'snort', 'whinny', 'tack'):
        cue(f'horse.{gait}', f'horse {gait}', 'SFX_Foley', status='blocked', attenuation='foley_mid',
            notes='Blocked on Freesound U2 (CC0 gallop 135 / snort 34 / whinny 40 sounds) or own recordings.')

    # ---------------- ambience per location / weather ----------------
    park = 'opengameart/park-ambiences'
    cue('amb.estate.day', 'Nyaagyu Estate, ch01 day', 'Ambience',
        layers=[cc0(park, 'birds'), cc0(park, 'wind'), cc0('opengameart/crow-caw')], loop=True, spatial=False,
        notes='Long CC0 field recordings (8+ min, 48 kHz); cut seamless loops at import. Uguisu / pheasant still '
              'needed (plan §3.11).')
    cue('amb.stream', 'river / stream emitters (estate, fields, silk foundry)', 'Ambience',
        layers=[cc0(park, 'river'), cc0('opengameart/water-waves')], loop=True, attenuation='ambient_emitter')
    cue('amb.rain', 'ch03 rain (卯の花腐し), rain weather state', 'Ambience',
        layers=[cc0('opengameart/rain-loopable', '.ogg'), cc0('opengameart/dripping-water-loop')], loop=True,
        spatial=False, notes='Plus eave-drip emitters from the drip loop. Heavy typhoon rain (ch07) still needed.')
    cue('amb.thunder', 'thunder one-shots (ch05 storm, ch07 typhoon)', 'Ambience',
        layers=[cc0('opengameart/rain-long-thunder')], attenuation='far', notes='Delay by distance; respect the '
        'flash-reduction setting for the paired lightning.')
    cue('amb.fire', 'burning estate (ch02), forge fire', 'Ambience',
        layers=[cc0('opengameart/fireplace-sound-loop'), cc0('opengameart/fire-crackling')], loop=True,
        attenuation='ambient_emitter')
    cue('amb.smithy', 'dojo smithy (ch01.b09), Silk Foundry (ch05)', 'Ambience',
        layers=[cc0('opengameart/68-workshop-sounds', 'hammering'), cc0('opengameart/blacksmiths-hammer', '.wav'),
                cc0('vcsl/Idiophones/Struck Idiophones/Anvil')], attenuation='ambient_emitter',
        notes='Anvil strikes double as the ch05 aizuchi percussion (100 BPM).')
    cue('amb.alien.flagship_engine', 'flagship 『複利号』 interiors (ch07)', 'Ambience',
        files=own('Original/Alien/amb_alien_engine_core_loop.wav'), loop=True, attenuation='ambient_emitter',
        pitch_cents=(0, 0))
    cue('amb.alien.ledger_engine', 'Reckoning / Ledger Engine (ch07.b06, ch08)', 'Ambience',
        files=own('Original/Alien/amb_alien_ledger_engine_loop.wav'), loop=True, attenuation='ambient_emitter',
        pitch_cents=(0, 0))
    cue('amb.alien.drone', 'Inventory drone hover (ch02+)', 'SFX_Alien',
        files=own('Original/Alien/amb_alien_drone_hover_loop_*.wav'), loop=True, attenuation='drone',
        pitch_cents=(-30, 30))
    cue('amb.alien.seizure_field', 'seizure field / debt seal field', 'SFX_Alien',
        files=own('Original/Alien/amb_alien_seizure_field_loop.wav'), loop=True, attenuation='ambient_emitter')
    cue('amb.alien.debt_terminal', 'debt terminal (ch03 notice square)', 'SFX_Alien',
        files=own('Original/Alien/amb_alien_debt_terminal_loop.wav'), loop=True, attenuation='ambient_emitter')
    cue('sfx.alien.sky_seam', 'ch01.b13 the sky splits', 'SFX_Alien', files=own('Original/Alien/sfx_alien_sky_seam_tear.wav'),
        spatial=False, max_instances=1, pitch_cents=(0, 0))
    cue('sfx.alien.debt_seal_clamp', 'ch02 debt seals clamp onto granaries', 'SFX_Alien',
        files=own('Original/Alien/sfx_alien_debt_seal_clamp_*.wav'), attenuation='weapon_mid')
    cue('amb.vault', 'Ledger vault (ch06): drips + distant engine', 'Ambience',
        layers=[cc0('opengameart/dripping-water-loop')], files=own('Original/Alien/amb_alien_ledger_engine_loop.wav'),
        loop=True, spatial=False, notes='Engine loop low-passed 800 Hz, -12 dB, as a far bed.')
    cue('amb.night_insects', 'late-summer night (ch06), dusk fields (ch04)', 'Ambience', status='needed',
        notes='Bell crickets, frogs, higurashi at dawn: Freesound CC0 after U2, or own field recording.')
    cue('amb.typhoon', 'ch07 typhoon beds (3 intensities) and gust riser', 'Ambience',
        layers=[cc0(park, 'wind')], status='needed', notes='Park wind is only a base; needs storm-strength beds.')
    cue('amb.festival', 'ch08 festival night', 'Ambience',
        layers=[cc0('opengameart/25-cc0-bang-firework-sfx', 'fw_')], status='needed',
        notes='Fireworks exist (CC0); crowd murmur and diegetic 祭囃子 are needed (crowd VO blocked on B6).')

    # ---------------- UI ----------------
    ui = [('ui.click', 'button press', 'ui_click_wood_*'), ('ui.hover', 'focus change', 'ui_hover_wood_*'),
          ('ui.confirm', 'confirm / accept', 'ui_confirm_rin.wav'), ('ui.back', 'back / cancel', 'ui_back_wood_*'),
          ('ui.error', 'invalid action', 'ui_error_knock_*'), ('ui.tab', 'tab switch', 'ui_tab_paper_*'),
          ('ui.menu.open', 'menu open', 'ui_menu_open_fusuma.wav'), ('ui.menu.close', 'menu close', 'ui_menu_close_fusuma.wav'),
          ('ui.notify', 'notification', 'ui_notify_bell_*'), ('ui.objective', 'objective updated', 'ui_objective_update_rin.wav'),
          ('ui.xor.credited', 'XOR payout / registry entry', 'ui_xor_credit_soroban_*'),
          ('ui.wallet.signed', 'IrohaConnect signature approved', 'ui_wallet_seal_stamp_*'),
          ('ui.slider', 'slider step', 'ui_slider_tick.wav'),
          ('ui.alien.chime', 'Credit House interface / PA chime', 'ui_alien_chime_*'),
          ('ui.alien.deny', 'Credit House terminal refuses', 'ui_alien_deny.wav')]
    for cid, trig, pat in ui:
        cue(cid, trig, 'UI', files=own(f'Original/UI/{pat}'), spatial=False, pitch_cents=(-20, 20), volume_db=(-0.5, 0))
    return {
        'schema_version': 1,
        'status': 'proposal: the engineering lane moves the approved subset into Content/Data (this file is not read '
                  'at runtime)',
        'generated_by': 'scripts/audio/build_cue_proposal.py',
        'generated_at_utc': datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        'events_source': 'Source/SoraArena/Public/SoraGameEvents.h (USoraGameEvents delegates)',
        'weapon_ids_source': 'Content/Data/catalog.json weapons[] and campaign_weapons[]',
        'sample_rate_hz': 48000,
        'buses': BUSES,
        'ducking': DUCKING,
        'attenuation_presets': ATTENUATION,
        'loudness': LOUDNESS,
        'music': music_block(),
        'cues': CUES,
    }


BUSES = [
    {'id': 'Master', 'parent': None, 'default_db': 0.0, 'user_slider': 'Master'},
    {'id': 'Music', 'parent': 'Master', 'default_db': -8.0, 'user_slider': 'Music'},
    {'id': 'SFX', 'parent': 'Master', 'default_db': 0.0, 'user_slider': 'SFX'},
    {'id': 'SFX_Weapons', 'parent': 'SFX', 'default_db': -2.0},
    {'id': 'SFX_Melee', 'parent': 'SFX', 'default_db': -1.0},
    {'id': 'SFX_Impacts', 'parent': 'SFX', 'default_db': -2.0},
    {'id': 'SFX_Explosions', 'parent': 'SFX', 'default_db': -3.0},
    {'id': 'SFX_Foley', 'parent': 'SFX', 'default_db': -4.0},
    {'id': 'SFX_Alien', 'parent': 'SFX', 'default_db': -4.0},
    {'id': 'SFX_Telegraph', 'parent': 'SFX', 'default_db': 0.0,
     'note': 'boss audio telegraphs: never ducked, never virtualised, audible when Music is 0'},
    {'id': 'Voice', 'parent': 'Master', 'default_db': 0.0, 'user_slider': 'Voice'},
    {'id': 'Voice_Barks', 'parent': 'Voice', 'default_db': 0.0, 'note': 'captioned boss barks (telegraphs)'},
    {'id': 'UI', 'parent': 'Master', 'default_db': -4.0, 'user_slider': 'UI'},
    {'id': 'Ambience', 'parent': 'Master', 'default_db': -3.0, 'user_slider': 'Ambience'},
]
DUCKING = [
    {'trigger': 'Voice', 'target': 'Music', 'db': -6.0, 'attack_ms': 80, 'release_ms': 450},
    {'trigger': 'Voice', 'target': 'Ambience', 'db': -4.0, 'attack_ms': 80, 'release_ms': 450},
    {'trigger': 'SFX_Telegraph', 'target': 'Music', 'db': -3.0, 'attack_ms': 20, 'release_ms': 300},
    {'trigger': 'SFX_Explosions', 'target': 'Ambience', 'db': -6.0, 'attack_ms': 10, 'release_ms': 800},
]
ATTENUATION = {
    'weapon_long': {'inner_m': 3, 'falloff_m': 80, 'lpf_far_hz': 3500, 'reverb_send': 'distance'},
    'weapon_mid': {'inner_m': 2, 'falloff_m': 45, 'lpf_far_hz': 4000},
    'melee_close': {'inner_m': 1, 'falloff_m': 25, 'lpf_far_hz': 5000},
    'foley_short': {'inner_m': 0.5, 'falloff_m': 15},
    'foley_mid': {'inner_m': 1, 'falloff_m': 30},
    'stealth_noise': {'inner_m': 1, 'falloff_m': 20, 'note': 'radius mirrors the AI hearing radius'},
    'explosion': {'inner_m': 5, 'falloff_m': 150, 'lpf_far_hz': 2500},
    'flyby': {'inner_m': 0.5, 'falloff_m': 12, 'doppler': True},
    'drone': {'inner_m': 2, 'falloff_m': 40, 'doppler': True},
    'ambient_emitter': {'inner_m': 3, 'falloff_m': 35},
    'far': {'inner_m': 50, 'falloff_m': 3000, 'distance_delay': True},
}
LOUDNESS = {
    'full_mix_integrated_lufs': -24.0,
    'full_mix_tolerance_lu': 2.0,
    'full_mix_true_peak_dbtp': -1.0,
    'reference': 'Sony ASWG-R001 home-console guideline (-24 LUFS +-2 LU); measure over 30+ min of play',
    'source_assets': {
        'music_loop_beds': {'integrated_lufs': -16.0, 'true_peak_dbtp': -1.0},
        'music_stingers': {'momentary_max_lufs': -16.0, 'true_peak_dbtp': -1.0},
        'ambience_beds': {'integrated_lufs': -26.0, 'true_peak_dbtp': -3.0},
        'alien_machinery_loops': {'integrated_lufs': '-24 (terminal -28)'},
        'weapon_loops_and_beams': {'integrated_lufs': '-18 to -22'},
        'sfx_one_shots_sustained': {'momentary_max_lufs': '-12 to -21 by category (see manifest targets)'},
        'sfx_one_shots_transient': {'true_peak_dbtp': '-1 (UI clicks -3, slider -12) after 3-9 dB of '
                                                      'oversampled soft-clip density; momentary loudness is reported'},
        'ui': {'momentary_max_lufs': '-19 to -26'},
        'dialogue': {'integrated_lufs': -20.0, 'true_peak_dbtp': -2.0, 'note': 'VO not recorded (B6/B7)'},
    },
}


def music_block() -> dict:
    mpath = ROOT / 'Content/SourceArt/Audio/Music/manifest.json'
    pieces = {p['name']: p for p in json.loads(mpath.read_text()).get('pieces', [])} if mpath.exists() else {}

    def piece_files(name):
        return sorted(str(p.relative_to(ROOT)) for p in (ROOT / f'{AUDIO}/Music/{name}').glob('*.wav'))
    return {
        'states': [
            {'state': 'title', 'piece': 'mus_title_nyaagyu_wind', 'files': piece_files('mus_title_nyaagyu_wind'),
             'handoff_sample': pieces.get('mus_title_nyaagyu_wind', {}).get('handoff_sample'),
             'note': 'Play _intro, start _loop at handoff_sample (sample-accurate, Quartz) while the intro tail rings. '
                     'Also the sketch of credits_main / ch03_oath (League theme).'},
            {'state': 'ch03_stealth', 'piece': 'mus_ch03_occupation_stealth',
             'files': piece_files('mus_ch03_occupation_stealth'),
             'stem_mix': {'unaware': ['base'], 'suspicious': ['base', 'pulse'], 'alert': ['base', 'pulse', 'perc'],
                          'search': ['base', 'pulse', 'search']},
             'crossfade_ms': {'into_alert': 250, 'out_of_alert': 2500, 'default': 1200},
             'note': 'All stems start together and loop together; switch states by fading stem gains only.'},
            {'state': 'mus_ch07_hangar / mus_boss_collatera P2', 'piece': 'mus_ch07_flagship_battle',
             'files': piece_files('mus_ch07_flagship_battle'),
             'stem_mix': {'P1_cold': ['synth'], 'P2_full': ['synth', 'taiko'], 'P3_duel': ['taiko']},
             'note': 'P3 in the design is taiko + a single tsuzumi; the tsuzumi layer is still needed.'},
        ],
        'states_needed': 'All other L5 states in docs/campaign/chapter-0N.md (music cue tables) are not written yet.',
        'rules': ['Loops are sample-exact; set the SoundWave looping and use the smpl loop / whole file.',
                  'Music bus at -8 dB default: a -16 LUFS bed sits about -24 LUFS in the full mix.',
                  'Stingers duck the bed -6 dB for their length; never stack two stingers.'],
    }


def main() -> int:
    payload = build()
    bus_ids = {b['id'] for b in BUSES}
    for c in payload['cues']:
        if c['bus'] not in bus_ids:
            ERRORS.append(f'cue {c["id"]}: unknown bus {c["bus"]}')
        if c['attenuation'] not in ATTENUATION and c['attenuation'] not in ('none', 'default'):
            ERRORS.append(f'cue {c["id"]}: unknown attenuation {c["attenuation"]}')
    if ERRORS:
        for e in ERRORS:
            print('ERROR', e)
        return 1
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    counts = {}
    for c in payload['cues']:
        counts[c['status']] = counts.get(c['status'], 0) + 1
    print(f'wrote {OUT.relative_to(ROOT)}: {len(payload["cues"])} cues {counts}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
