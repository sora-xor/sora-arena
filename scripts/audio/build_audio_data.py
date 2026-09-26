#!/usr/bin/env python3
"""Build Content/Data/audio.json, the runtime audio data USoraAudioSubsystem reads.

The cue proposal (Content/SourceArt/Audio/cues.proposed.json, built by
build_cue_proposal.py) stays the record of what was proposed and which CC0
layers each cue still wants. This script moves the approved runtime subset into
Content/Data and adds what the game needs to play it:

* ``buses``: the bus tree of docs/audio.md section 2, each with its user slider,
  its submix parent and, for the two telegraph buses, the volume floor that
  keeps them audible at low SFX and Voice settings (so their submixes feed
  Master directly);
* ``attenuation``: the proposal's 3D presets;
* ``cues``: every cue with the waves it plays (paths relative to both
  Content/SourceArt/Audio and /Game/Generated/Audio): the OWN renders, or the
  CC0 recordings build_cc0_audio.py admitted (Content/SourceArt/Audio/CC0,
  status ready-cc0, or placeholder-cc0 for Kenney stand-ins); its bus,
  attenuation, concurrency, randomisation, caption key and, for telegraphs,
  the strike mark the difficulty-scaled windup is aligned to. A cue whose
  sound does not exist yet keeps its place with no waves and says what it
  still needs, as does a placeholder;
* ``bindings``: for every event family (the USoraGameEvents delegates, the
  practice kernel's events, the front end's sounds, and what the subsystem
  polls: the hero's weapon actions, footsteps and horses) the ordered rules
  that pick a cue from the event's fields;
* ``music``: the three written pieces, the five music states the runtime moves
  between (menu, exploration, stealth, combat, boss), their stem mixes and
  crossfades, and the stinger rule;
* ``beats``: every campaign beat's place, music id and state, sparring weapon,
  ambience bed, weather and default footstep surface, from the chapter files;
  ``maps`` does the same for the practice arenas;
* ``telegraphs``: the telegraph sound class of every boss and enemy attack,
  from bosses.json and enemies.json.

Usage: ``python3 scripts/audio/build_audio_data.py`` writes the file;
``--check`` exits nonzero when the committed file differs from a fresh build.
scripts/audio/validate_audio_data.py checks the result against the game.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROPOSAL = ROOT / 'Content/SourceArt/Audio/cues.proposed.json'
CC0_MANIFEST = ROOT / 'Content/SourceArt/Audio/CC0/manifest.json'
OUT = ROOT / 'Content/Data/audio.json'
DATA = ROOT / 'Content/Data'
SOURCE_PREFIX = 'Content/SourceArt/Audio/'
SCHEMA = 1

# ---------------------------------------------------------------------------
# Buses. Telegraph buses keep a floor (docs/audio.md section 2, 5): at any SFX
# or Voice setting they play at no less than -12 dB, so their submixes route
# straight to Master and carry max(parent slider, floor) themselves.
TELEGRAPH_FLOOR_DB = -12.0
FLOORED = {'SFX_Telegraph': 'SFX', 'Voice_Barks': 'Voice'}

# ---------------------------------------------------------------------------
# Cue edits on top of the proposal. Multi-part proposal cues become one cue per
# part, so a random pick never plays a loop or a stop as a shot.
DROPPED = {
    # The beam itself is the boss's WeaponFired (Kind Beam): projectile.beam.
    'boss.strike.beam': 'the boss beam sounds through WeaponFired (Kind Beam, projectile.beam)',
}
WAVE_EDITS = {
    'weapon.fired.shock_emitter': ['Original/Weapons/wpn_shock_emitter_start'],
    'projectile.beam': ['Original/Weapons/wpn_energy_beam_start'],
    'boss.strike.cleave': ['Original/Melee/mel_whoosh_kanabo_01', 'Original/Melee/mel_whoosh_kanabo_02'],
    'site.restored': ['Music/Stingers/mus_sting_site_restored'],
    'boss.windup.area_1500': ['Original/Telegraphs/tel_cleave_amber_02'],
    # shd_barrier_regen is the boss shield's telegraph (SFX_Telegraph); the
    # lance needs its own warm heal voice rather than a telegraph.
    'weapon.fired.healing_lance': [],
}
SITE_RESTORED_BUS = 'Music'
# Beds the proposal left as one-shots because nothing plays them yet.
LOOP_EDITS = {'amb.night_insects', 'amb.typhoon', 'amb.festival'}
ADDED_CUES = [
    {'id': 'weapon.loop.shock_emitter', 'bus': 'SFX_Weapons', 'status': 'ready-own',
     'waves': ['Original/Weapons/wpn_shock_emitter_loop'], 'attenuation': 'weapon_mid', 'loop': True,
     'max_instances': 3, 'notes': 'Sustain loop while the Shock Emitter keeps firing (weapon.fired.shock_emitter).'},
    {'id': 'weapon.release.shock_emitter', 'bus': 'SFX_Weapons', 'status': 'ready-own',
     'waves': ['Original/Weapons/wpn_shock_emitter_stop'], 'attenuation': 'weapon_mid', 'loop': False,
     'max_instances': 3, 'notes': 'Tail when the Shock Emitter stops firing.'},
    {'id': 'weapon.loop.beam', 'bus': 'SFX_Weapons', 'status': 'ready-own',
     'waves': ['Original/Weapons/wpn_energy_beam_loop'], 'attenuation': 'weapon_long', 'loop': True,
     'max_instances': 3, 'notes': 'Sustain loop while a beam keeps firing (projectile.beam).'},
    {'id': 'weapon.release.beam', 'bus': 'SFX_Weapons', 'status': 'ready-own',
     'waves': ['Original/Weapons/wpn_energy_beam_stop'], 'attenuation': 'weapon_long', 'loop': False,
     'max_instances': 3, 'notes': 'Tail when a beam stops.'},
    {'id': 'weapon.fired.boss_round', 'bus': 'SFX_Weapons', 'status': 'ready-own',
     'waves': [f'Original/Weapons/wpn_pulse_carbine_fire_0{n}' for n in range(1, 5)],
     'attenuation': 'weapon_long', 'loop': False, 'max_instances': 6, 'pitch_cents': [-180, -120],
     'notes': "A boss's own rounds (WeaponId none): the pulse carbine a whole tone down until each boss has its voice."},
    {'id': 'boss.windup.margin_call', 'bus': 'SFX_Telegraph', 'status': 'ready-own',
     'waves': ['Original/Telegraphs/tel_margin_call_riser_1500ms'], 'attenuation': '', 'loop': False,
     'max_instances': 2, 'strike_ms': 1500, 'pitch_cents': [0, 0],
     'notes': "Collatera's 追証 margin call: the riser ends clipped at the 1500 ms strike."},
    {'id': 'enemy.windup.lock', 'bus': 'SFX_Telegraph', 'status': 'ready-own',
     'waves': ['Original/Telegraphs/tel_lock_cyan_900ms'], 'attenuation': 'weapon_mid', 'loop': False,
     'max_instances': 3, 'strike_ms': 900, 'pitch_cents': [0, 0], 'caption': 'TargetingLock',
     'notes': 'A cyan (locked-aim) attack of an ordinary opponent: marksman lock, walker beam, drone net.'},
    {'id': 'melee.marobashi', 'bus': 'SFX_Foley', 'status': 'needed', 'waves': [], 'attenuation': 'foley_short',
     'loop': False, 'max_instances': 2, 'needs': 'cloth and armour roll foley for 転',
     'notes': 'The hero rolls to the flank (OnMarobashi).'},
    {'id': 'horse.canter', 'bus': 'SFX_Foley', 'status': 'blocked', 'waves': [], 'attenuation': 'foley_mid',
     'loop': False, 'max_instances': 4, 'needs': 'unshod three-beat canter footfalls (Freesound U2 or own recording)',
     'notes': 'Three-beat canter footfalls.'},
]
# Cues whose files are layers for a MetaSound that does not exist yet: imported,
# never played directly.
UNBOUND_CUES = {
    'melee.parry.layers': 'clang, scrape, sparks and body layers for the parry MetaSound (scaled by parry quality)',
    'weapon.yumi.nock': 'no nock event yet: the hero nocks as part of the draw',
    'projectile.arrow.flyby': 'needs a pass-by detector for arrows near the listener',
    'amb.stream': 'a positioned emitter at streams; the chapter layouts name no stream emitters yet',
    'amb.smithy': 'a positioned emitter at forges; the chapter layouts name no forge emitters yet',
    'amb.alien.debt_terminal': 'a positioned emitter at debt terminals; the layouts name none yet',
    'barrier.hum': 'needs the boss shield state; ASoraBoss exposes only its shield events',
    'horse.snort': 'no calm-down event on the horse yet',
    'ui.wallet.signed': 'the wallet screen does not announce an approved signature yet',
    'ui.alien.deny': 'no Credit House terminal refuses the hero yet',
    'boss.shield.regen': 'ASoraBoss announces a shield breaking, not regenerating',
}
CAPTIONS = {
    # Cue id -> caption key (NSLOCTEXT "SoraArena.SoundCaptions" in
    # Source/SoraArena/Private/Audio/SoraSoundCaptions.cpp). USoraCaptions
    # already captions other combatants' shots and swings, blades meeting,
    # explosions and a boss's arrival, windups and defeat; these add what it
    # does not hear.
    'weapon.reload.cell_eject': 'CellEjects',
    'boss.shield.break': 'BarrierShatters',
    'boss.shield.regen': 'BarrierRecharging',
    'foot.nightingale_floor': 'NightingaleFloor',
    'enemy.windup.lock': 'TargetingLock',
    'sfx.alien.sky_seam': 'SkySplits',
    'sfx.alien.debt_seal_clamp': 'DebtSealsClamp',
    'ui.alien.chime': 'CreditHouseChime',
}
# The hero's own step on a nightingale floor is exactly what must be captioned.
CAPTION_HERO = {'foot.nightingale_floor'}
STINGERS = {'player.died', 'sparring.point', 'boss.arrived', 'boss.defeated', 'chapter.started',
            'chapter.completed', 'site.restored'}
# Telegraph files: where the strike lands in the file (docs/audio.md 3.4).
STRIKE_MS = {'boss.windup.beam': 900, 'boss.windup.cleave': 900, 'boss.windup.area_1500': 1500}
# A repeated shot within gap_ms keeps a loop running; the release plays after.
SUSTAIN = {
    'weapon.fired.shock_emitter': {'loop': 'weapon.loop.shock_emitter', 'release': 'weapon.release.shock_emitter',
                                   'gap_ms': 450},
    'projectile.beam': {'loop': 'weapon.loop.beam', 'release': 'weapon.release.beam', 'gap_ms': 450},
}
NEEDS = {
    'weapon.fired.healing_lance': 'a warm heal voice of our own',
    'weapon.yumi.nock': 'CC0 nock layers',
    'projectile.arrow.flyby': 'CC0 arrow pass-by layers',
    'boss.defeated': 'a release sting per boss (placeholder: the boss phase sting)',
    'foot.wood': 'suri-ashi on hinoki (the board creak is only its quiet stealth layer)',
    'foot.gravel': 'gravel steps',
    'foot.metal_grating': 'gantry grating steps',
    'horse.walk': 'unshod hooves (Freesound U2 or own recording)',
    'horse.trot': 'unshod hooves (Freesound U2 or own recording)',
    'horse.gallop': 'unshod hooves (Freesound U2 or own recording)',
    'horse.snort': 'snorts (Freesound U2)',
    'horse.whinny': 'whinnies (Freesound U2)',
    'horse.tack': 'bit, abumi and saddle creak',
    'amb.stream': 'CC0 small-river recording',
    'amb.smithy': 'CC0 workshop hammering and anvils',
    'amb.vault': 'CC0 drips over the low-passed Ledger Engine (plays the engine alone for now)',
    'amb.night_insects': 'night insects and frogs',
}
# Cues the admitted CC0 recordings voice (Content/SourceArt/Audio/CC0), and
# what would still make them right. Kenney files are placeholders by their
# ledger ("never a hero sound"): their cues are placeholder-cc0.
CC0_PLACEHOLDERS = {'melee.strike.hit_body', 'enemy.died', 'foot.grass', 'foot.tatami'}
STILL_WANTED = {
    'weapon.fired.yumi': 'the tsurune and yugaeri of a real yumi (own recording); CC0 longbow and recurve releases stand in',
    'weapon.yumi.draw': "a yumi's own draw (own recording); CC0 longbow and recurve creaks stand in",
    'weapon.fired.grenade_launcher': 'a launcher tube layer over the CC0 shot and cannon body',
    'explosion.detonated': 'a debris layer over the CC0 bang and muffled body',
    'melee.katana.draw': 'the nōtō click needs close foley',
    'melee.katana.sheathe': 'the nōtō click needs close foley',
    'melee.strike.hit_body': "own cloth, armour and cut foley; Kenney's heavy punch stands in",
    'enemy.died': "a body fall and armour rattle of our own; Kenney's heavy soft impact stands in",
    'foot.grass': "grass steps of our own; Kenney's grass steps stand in",
    'foot.tatami': "tatami (igusa) steps of our own; Kenney's carpet steps stand in",
    'amb.estate.day': 'uguisu and pheasant calls over the CC0 park birds',
    'amb.typhoon': 'wind beds in three intensities and a gust riser; CC0 park wind and rain stand in',
    'amb.festival': 'crowd and 祭囃子 under the CC0 fireworks',
}

# ---------------------------------------------------------------------------
# Event bindings: family -> ordered rules. Each rule's `when` names event
# fields (validate_audio_data.py lists them per family); the first matching
# rule plays its cue unless it says `continue`, and a rule may delay its cue.
MELEE_WEAPONS = {0: 'katana', 4: 'wakizashi', 10: 'tanto'}


def rule(cue, when=None, cont=False, delay_ms=0):
    return {'when': when or {}, 'cue': cue, 'continue': cont, 'delay_ms': delay_ms}


def weapon_rules():
    rules = [
        rule('projectile.beam', {'Kind': 'Beam'}),
        rule('weapon.fired.boss_round', {'WeaponId': -1, 'Kind': 'Hitscan'}),
    ]
    fired = {1: 'arc_carbine', 3: 'needle_smg', 5: 'coil_matchlock', 7: 'grenade_launcher', 9: 'repeater',
             11: 'pulse_carbine', 13: 'phantom_smg', 14: 'plasma_matchlock', 15: 'micro_mortar',
             16: 'shock_emitter', 17: 'healing_lance', 18: 'yumi'}
    rules += [rule(f'weapon.fired.{name}', {'WeaponId': weapon}) for weapon, name in fired.items()]
    return rules


def melee_rules():
    rules = [
        rule('melee.committed.bokuto', {'Sparring': 'bokuto'}),
        rule('melee.committed.fukuro_shinai', {'Sparring': 'fukuro_shinai'}),
    ]
    for weapon, name in MELEE_WEAPONS.items():
        rules.append(rule(f'melee.committed.{name}.heavy', {'WeaponId': weapon, 'WindupSeconds': '>=0.5'}))
        rules.append(rule(f'melee.committed.{name}', {'WeaponId': weapon}))
    rules += [
        rule('melee.committed.naginata', {'WeaponId': [12, 20]}),
        rule('melee.committed.yari', {'WeaponId': 19}),
        rule('melee.committed.kusarigama', {'WeaponId': 2}),
        rule('melee.committed.kanabo', {'WeaponId': [6, 8]}),
    ]
    return rules


BINDINGS = {
    'WeaponFired': weapon_rules(),
    'MeleeCommitted': melee_rules(),
    'StrikeResolved': [
        rule('melee.dojo.clack', {'bHit': True, 'Sparring': ['bokuto', 'fukuro_shinai']}),
        rule('melee.strike.hit_body', {'bHit': True}),
    ],
    'Guarded': [rule('melee.dojo.clack', {'bDojo': True}), rule('melee.guard')],
    'Parried': [rule('melee.dojo.clack', {'bDojo': True}), rule('melee.parry')],
    'Marobashi': [rule('melee.marobashi')],
    'Damaged': [rule('player.damaged', {'VictimIsHero': True})],
    'Died': [
        rule('sparring.point', {'bSparring': True}),
        rule('player.died', {'VictimIsHero': True}),
        rule('enemy.died'),
    ],
    'Detonated': [rule('explosion.detonated')],
    'EnemyCue': [
        rule('enemy.windup.lock', {'Cue': 'AttackWindup', 'Telegraph': 'lock'}),
        rule('boss.shield.break', {'Cue': 'BarrierBroken'}),
        rule('boss.shield.hit', {'Cue': 'ShieldTurned'}),
        rule('ui.alien.chime', {'Cue': 'Alarm'}),
    ],
    'SiteRestored': [rule('site.restored', cont=True), rule('ui.xor.credited', {'bCampaign': True})],
    'ChapterStarted': [rule('chapter.started', {'bResumed': False})],
    'ChapterCompleted': [rule('chapter.completed')],
    'BossPhase': [
        rule('boss.arrived', {'Phase': 'Arrived'}),
        rule('weapon.reload.cell_eject', {'Phase': 'Windup', 'Telegraph': 'reload'}),
        rule('boss.windup.beam', {'Phase': 'Windup', 'Telegraph': 'lock'}),
        rule('boss.windup.margin_call', {'Phase': 'Windup', 'Telegraph': 'margin_call'}),
        rule('boss.windup.area_1500', {'Phase': 'Windup', 'Telegraph': 'area'}),
        rule('boss.windup.cleave', {'Phase': 'Windup', 'Telegraph': 'cleave'}),
        rule('boss.strike.cleave', {'Phase': 'Strike', 'bBeam': False, 'Telegraph': ['cleave', 'area']}),
        rule('boss.shield.break', {'Phase': 'Event', 'Detail': ['shield_broken', 'barrier_broken', 'mantle_down',
                                                                 'ward_broken', 'wards_broken', 'weakpoint_destroyed',
                                                                 'shield_down', 'barrier_burnout']}),
        rule('boss.shield.hit', {'Phase': 'Event', 'Detail': ['deflected', 'front_blocked', 'ward_blocked']}),
        rule('melee.parry', {'Phase': 'Countered'}),
        rule('boss.defeated', {'Phase': 'Defeated'}),
    ],
    'BeatStarted': [
        rule('sfx.alien.sky_seam', {'BeatId': 'ch01.b13', 'bResumed': False}),
        rule('sfx.alien.debt_seal_clamp', {'BeatId': 'ch02.b01', 'bResumed': False}),
    ],
    'BeatCompleted': [rule('ui.objective', {'bOptional': False})],
    'BeatFailed': [],
    'Kernel': [
        # A kernel shot is a weapon's discharge: melee arms sound as a swing.
        {'when': {'Kind': 'Shot', 'WeaponKind': 'melee'}, 'as': 'MeleeCommitted', 'continue': False, 'delay_ms': 0},
        {'when': {'Kind': 'Shot'}, 'as': 'WeaponFired', 'continue': False, 'delay_ms': 0},
        {'when': {'Kind': ['Damage', 'HazardDamage']}, 'as': 'Damaged', 'continue': False, 'delay_ms': 0},
        {'when': {'Kind': 'Death'}, 'as': 'Died', 'continue': False, 'delay_ms': 0},
        {'when': {'Kind': 'Guarded', 'Detail': 1}, 'as': 'Parried', 'continue': False, 'delay_ms': 0},
        {'when': {'Kind': 'Guarded'}, 'as': 'Guarded', 'continue': False, 'delay_ms': 0},
        rule('melee.parry', {'Kind': 'Riposte'}),
        rule('ui.notify', {'Kind': 'Respawn', 'TargetIsHero': True}),
        rule('boss.shield.break', {'Kind': 'EntityDestroyed', 'Detail': 1}),
        rule('ui.objective', {'Kind': ['ObjectiveCaptured', 'Checkpoint']}),
        rule('ui.notify', {'Kind': 'Overtime'}),
        rule('chapter.completed', {'Kind': 'MatchWinner', 'HeroWon': True}),
    ],
    'UI': [
        rule('ui.hover', {'Sound': 'Hover'}),
        rule('ui.click', {'Sound': 'Click'}),
        rule('ui.confirm', {'Sound': 'Confirm'}),
        rule('ui.back', {'Sound': 'Back'}),
        rule('ui.error', {'Sound': 'Error'}),
        rule('ui.tab', {'Sound': 'Option'}),
        rule('ui.slider', {'Sound': 'Slider'}),
        rule('ui.menu.open', {'Sound': 'MenuOpen'}),
        rule('ui.menu.close', {'Sound': 'MenuClose'}),
    ],
    'Hero': [
        rule('weapon.reload.cell_eject', {'Action': 'ReloadStarted', 'WeaponId': [1, 3, 11, 13, 14, 16, 17]}),
        rule('weapon.charge.plasma_matchlock', {'Action': 'ChargeStarted', 'WeaponId': 14}),
        rule('weapon.hold.plasma_matchlock', {'Action': 'ChargeHeld', 'WeaponId': 14}),
        rule('weapon.yumi.draw', {'Action': 'BowDrawn'}),
        rule('melee.katana.sheathe', {'Action': 'Sheathed'}),
        rule('melee.katana.draw', {'Action': 'Drawn'}),
    ],
    'Footstep': [
        rule(f'foot.{surface}', {'Surface': surface})
        for surface in ('wood', 'tatami', 'earth', 'stone', 'grass', 'water', 'gravel', 'nightingale_floor',
                        'metal_grating')
    ],
    'Horse': [
        rule('horse.walk', {'Action': 'Hoof', 'Gait': 'Walk'}),
        rule('horse.trot', {'Action': 'Hoof', 'Gait': 'Trot'}),
        rule('horse.canter', {'Action': 'Hoof', 'Gait': 'Canter'}),
        rule('horse.gallop', {'Action': 'Hoof', 'Gait': 'Gallop'}),
        rule('horse.whinny', {'Action': 'Spooked'}),
        rule('horse.tack', {'Action': ['Mounted', 'Dismounted']}),
    ],
}
# Families or kernel kinds deliberately without a sound, and why.
UNBOUND_EVENTS = {
    'BeatFailed': 'the hero falling already plays player.died; the checkpoint reload needs no sound',
    'Kernel.Terminal': 'the match winner plays first; terminal only closes the step',
    'Kernel.Healed': "the lance's own shot sounds (weapon.fired.healing_lance)",
    'Kernel.Ability': 'the class abilities have no sounds yet',
    'Kernel.Marked': 'the Teppō mark has no sound yet',
    'Kernel.EntitySpawned': 'deployables have no placement sounds yet',
    'Kernel.EntityDamaged': 'deployables have no damage sounds yet',
    'Kernel.EntityRepaired': 'deployables have no repair sounds yet',
}

# ---------------------------------------------------------------------------
# Music: the three written pieces and the states the runtime moves between.
PIECES = {
    'title': {'bpm': 66, 'beats_per_bar': 4, 'intro': 'Music/mus_title_nyaagyu_wind/mus_title_nyaagyu_wind_intro',
              'handoff_bars': 4, 'handoff_sample': 698182,
              'stems': {'main': 'Music/mus_title_nyaagyu_wind/mus_title_nyaagyu_wind_loop'}, 'full': ''},
    'occupation': {'bpm': 84, 'beats_per_bar': 4, 'intro': '', 'handoff_bars': 0, 'handoff_sample': 0,
                   'stems': {name: f'Music/mus_ch03_occupation_stealth/mus_ch03_occupation_stealth_stem_{name}'
                             for name in ('base', 'pulse', 'perc', 'search')},
                   'full': 'Music/mus_ch03_occupation_stealth/mus_ch03_occupation_stealth_loop'},
    'flagship': {'bpm': 132, 'beats_per_bar': 4, 'intro': '', 'handoff_bars': 0, 'handoff_sample': 0,
                 'stems': {name: f'Music/mus_ch07_flagship_battle/mus_ch07_flagship_battle_stem_{name}'
                           for name in ('synth', 'taiko')},
                 'full': 'Music/mus_ch07_flagship_battle/mus_ch07_flagship_battle_loop'},
}
STATES = {
    'menu': {'piece': 'title', 'intro': True, 'mixes': {'default': ['main']}, 'phase_mixes': []},
    'exploration': {'piece': 'title', 'intro': False, 'mixes': {'default': ['main']}, 'phase_mixes': []},
    'stealth': {'piece': 'occupation', 'intro': False,
                'mixes': {'default': ['base'], 'unaware': ['base'], 'suspicious': ['base', 'pulse'],
                          'search': ['base', 'pulse', 'search']}, 'phase_mixes': []},
    'combat': {'piece': 'occupation', 'intro': False, 'mixes': {'default': ['base', 'pulse', 'perc']},
               'phase_mixes': []},
    'boss': {'piece': 'flagship', 'intro': False, 'mixes': {'default': ['synth']},
             'phase_mixes': [['synth'], ['synth', 'taiko'], ['taiko']]},
}
# AlertState details (ESoraEnemyCue::AlertState) and how loud each is; the
# loudest guard sets the stealth mix, and alert or combat turns it to combat.
ALERT_LEVELS = {'unaware': 0, 'retreat': 0, 'suspicious': 1, 'search': 2, 'alert': 3, 'combat': 3}

# ---------------------------------------------------------------------------
# Places: ambience bed, weather and default footstep surface for every place
# of every chapter (a place can recur in another chapter with other weather).
PLACES = {
    1: {
        'pl_tsumagizaka_dojo': ('amb.estate.day', 'clear', 'wood'),
        'pl_estate_day': ('amb.estate.day', 'clear', 'earth'),
        'pl_umaya': ('amb.estate.day', 'clear', 'earth'),
        'pl_matoba': ('amb.estate.day', 'clear', 'earth'),
        'pl_issoseki_wood': ('amb.estate.day', 'clear', 'grass'),
        'pl_dojo_smithy': ('amb.estate.day', 'clear', 'earth'),
    },
    2: {
        'pl_estate_night': ('amb.night_insects', 'fire', 'earth'),
        'pl_bugugura': ('amb.night_insects', 'fire', 'earth'),
        'pl_kaido': ('amb.night_insects', 'clear', 'earth'),
        'pl_ishibashi': ('amb.night_insects', 'clear', 'stone'),
        'pl_kakuredani': ('amb.estate.day', 'clear', 'earth'),
    },
    3: {
        'pl_horiwari': ('', 'rain', 'wood'),
        'pl_lantern_ward_rain': ('', 'rain', 'stone'),
        'pl_ura_nagaya': ('', 'rain', 'earth'),
        'pl_kido': ('', 'rain', 'earth'),
        'pl_chochin_kobo': ('', 'rain', 'tatami'),
        'pl_kosatsuba': ('', 'rain', 'stone'),
        'pl_chochin_gashi': ('', 'rain', 'wood'),
    },
    4: {
        'pl_shoya_yashiki': ('amb.estate.day', 'clear', 'tatami'),
        'pl_shimomura': ('amb.estate.day', 'clear', 'earth'),
        'pl_otameike': ('amb.estate.day', 'clear', 'stone'),
        'pl_tanada': ('amb.estate.day', 'clear', 'grass'),
        'pl_suisha_goya': ('amb.estate.day', 'clear', 'wood'),
        'pl_gogura': ('amb.estate.day', 'clear', 'wood'),
    },
    5: {
        'pl_kanna_nagashi': ('amb.night_insects', 'clear', 'water'),
        'pl_silk_foundry': ('amb.night_insects', 'clear', 'earth'),
        'pl_itotoriba': ('', 'clear', 'wood'),
        'pl_hataba': ('', 'clear', 'wood'),
        'pl_takadono': ('amb.fire', 'clear', 'earth'),
        'pl_okaji': ('amb.fire', 'clear', 'earth'),
        'pl_aratamejo': ('', 'clear', 'wood'),
        'pl_sumigoya': ('amb.night_insects', 'clear', 'earth'),
        'pl_toritategura': ('', 'clear', 'wood'),
        'pl_imonoba': ('amb.fire', 'clear', 'earth'),
    },
    6: {
        'pl_kosatsuba': ('amb.estate.day', 'clear', 'stone'),
        'pl_citadel_moat': ('amb.night_insects', 'fog', 'stone'),
        'pl_ishigaki': ('amb.night_insects', 'fog', 'stone'),
        'pl_relay_room': ('amb.vault', 'clear', 'stone'),
        'pl_ledger_corridors': ('amb.vault', 'clear', 'wood'),
        'pl_uguisu_hall': ('amb.vault', 'clear', 'nightingale_floor'),
        'pl_archive': ('amb.vault', 'clear', 'wood'),
        'pl_press_hall': ('amb.vault', 'clear', 'wood'),
        'pl_vault_core': ('amb.alien.ledger_engine', 'clear', 'metal_grating'),
    },
    7: {
        'pl_kakuredani': ('amb.night_insects', 'clear', 'earth'),
        'pl_anchor_bastion': ('', 'typhoon', 'stone'),
        'pl_cargo_hold': ('amb.alien.flagship_engine', 'clear', 'metal_grating'),
        'pl_seized_vault': ('amb.alien.flagship_engine', 'clear', 'metal_grating'),
        'pl_reckoning_engine': ('amb.alien.ledger_engine', 'clear', 'metal_grating'),
        'pl_hangar': ('amb.alien.flagship_engine', 'clear', 'metal_grating'),
        'pl_hull_ridge': ('', 'typhoon', 'metal_grating'),
        'pl_bridge_approach': ('amb.alien.flagship_engine', 'clear', 'metal_grating'),
        'pl_bridge': ('amb.alien.flagship_engine', 'clear', 'metal_grating'),
        'pl_kayanohara': ('', 'typhoon', 'grass'),
    },
    8: {
        'pl_kakuredani': ('amb.estate.day', 'clear', 'earth'),
        'pl_causeway': ('amb.estate.day', 'clear', 'earth'),
        'pl_outer_bailey': ('amb.estate.day', 'fire', 'gravel'),
        'pl_otemon': ('amb.estate.day', 'fire', 'stone'),
        'pl_collateral_cells': ('amb.vault', 'clear', 'stone'),
        'pl_ledger_spire': ('amb.alien.ledger_engine', 'clear', 'metal_grating'),
        'pl_ledger_engine': ('amb.alien.ledger_engine', 'clear', 'metal_grating'),
        'pl_lantern_ward_festival': ('amb.night_insects', 'festival', 'stone'),
        'pl_higashi_torii': ('amb.estate.day', 'clear', 'gravel'),
    },
}
WEATHER = {'clear': '', 'fog': '', 'rain': 'amb.rain', 'sun_shower': 'amb.rain', 'typhoon': 'amb.typhoon',
           'fire': 'amb.fire', 'festival': 'amb.festival'}
# Beat-level weather from the chapter files' ext (environment.weather and
# weather_events); a sun shower that switches on mid-beat plays from its start.
BEAT_WEATHER = {'typhoon_front': 'typhoon', 'sun_shower_on': 'sun_shower'}
# The practice arenas (catalog maps 0-3).
MAPS = {
    0: ('amb.estate.day', 'clear', 'earth'),
    1: ('', 'rain', 'stone'),
    2: ('amb.night_insects', 'clear', 'earth'),
    3: ('amb.vault', 'fog', 'stone'),
}

# ---------------------------------------------------------------------------
# Footsteps and horses.
FOOTSTEPS = {
    # The environment palette's material roles (MI_Nyaagyu_<Role>) and what a
    # step on each sounds like; the place's surface covers anything else.
    'materials': {'Timber': 'wood', 'Stone': 'stone', 'Metal': 'metal_grating', 'Plaster': 'stone',
                  'Kawara': 'stone', 'Soil': 'earth', 'TerrainSoil': 'earth', 'TerrainStone': 'stone',
                  'ToriiLacquer': 'wood'},
    # A stealth floor this loud is a nightingale floor (SoraStealthRules: walk 3000).
    'nightingale_permille': 3000,
    'surfaces': {surface: f'foot.{surface}' for surface in ('wood', 'tatami', 'earth', 'stone', 'grass', 'water',
                                                            'gravel', 'nightingale_floor', 'metal_grating')},
    'stride_cm': {'crouch': 55, 'walk': 80, 'run': 115},
    'run_speed_cm_s': 450,
    'min_speed_cm_s': 40,
    'pace_db': {'crouch': -9.0, 'walk': -3.0, 'run': 0.0},
    'range_m': 25,
}
HORSES = {
    # Hoofbeats per second at each gait (a native horse, bible section 4.5):
    # a four-beat walk, a two-beat trot, a three-beat canter, a four-beat gallop.
    'hoofbeats_per_s': {'Walk': 3.4, 'Trot': 2.8, 'Canter': 4.2, 'Gallop': 7.2},
    'range_m': 60,
}
# Loops that ride on an opponent while it lives, by enemies.json archetype.
ATTACHED = {'drone': 'amb.alien.drone', 'seizure_walker': 'amb.alien.seizure_field'}

# ---------------------------------------------------------------------------
LOCK_KINDS_NONE = {'summon', 'expose', 'step'}
SPECIAL_ATTACKS = {('boss_collatera', 'margin_call'): 'margin_call', ('boss_collatera', 'reload'): 'reload'}
AREA_WINDUP_MS = 1200


def fail(message):
    sys.exit(f'build_audio_data: {message}')


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def wave_of(source):
    if not source.startswith(SOURCE_PREFIX) or not source.endswith('.wav'):
        fail(f'not a project wave: {source}')
    return source[len(SOURCE_PREFIX):-4]


def build_buses(proposal):
    buses = []
    for bus in proposal['buses']:
        floored = FLOORED.get(bus['id'])
        buses.append({
            'id': bus['id'], 'parent': bus['parent'] or '',
            'submix_parent': 'Master' if floored else (bus['parent'] or ''),
            'default_db': bus['default_db'], 'slider': bus.get('user_slider', ''),
            'floor_of': floored or '', 'floor_db': TELEGRAPH_FLOOR_DB if floored else 0.0,
        })
    return buses


def build_attenuation(proposal):
    presets = {}
    for name, preset in proposal['attenuation_presets'].items():
        presets[name] = {
            'inner_m': preset['inner_m'], 'falloff_m': preset['falloff_m'],
            'lpf_far_hz': preset.get('lpf_far_hz', 0), 'reverb_send': preset.get('reverb_send') == 'distance',
            'doppler': bool(preset.get('doppler', False)), 'distance_delay': bool(preset.get('distance_delay', False)),
        }
    return presets


def needs(cue, status, waves):
    if status in ('ready-cc0', 'placeholder-cc0'):
        return STILL_WANTED.get(cue['id'], '')
    if waves and status == 'ready-own':
        return ''
    if cue['id'] in NEEDS:
        return NEEDS[cue['id']]
    layers = sorted({layer['asset_id'] for layer in cue['layers_cc0']})
    return f"its CC0 layers ({', '.join(layers)}) are local-private" if layers else ''


def cc0_waves():
    """Cue id -> the CC0 derivatives build_cc0_audio.py made for it, in name order."""
    waves = {}
    for record in read(CC0_MANIFEST)['records']:
        for row in record['files']:
            waves.setdefault(row['cue'], []).append(wave_of(row['file']))
    return {cue: sorted(names) for cue, names in waves.items()}


def build_cues(proposal):
    cues = []
    cc0 = cc0_waves()
    for cue in proposal['cues']:
        cue_id = cue['id']
        if cue_id in DROPPED:
            continue
        waves = WAVE_EDITS.get(cue_id, [wave_of(file) for file in cue['files']])
        status = cue['status']
        if cue_id in cc0:
            if waves:
                fail(f'{cue_id} would mix OWN and CC0 waves')
            waves = cc0[cue_id]
            status = 'placeholder-cc0' if cue_id in CC0_PLACEHOLDERS else 'ready-cc0'
            if status == 'placeholder-cc0' and cue_id not in STILL_WANTED:
                fail(f'placeholder {cue_id} must say what replaces it')
        # 'none' and 'default' are 2D: beds, stingers, interface and telegraphs.
        attenuation = cue['attenuation'] if cue['attenuation'] not in ('none', 'default') else ''
        bus = SITE_RESTORED_BUS if cue_id == 'site.restored' else cue['bus']
        entry = {
            'id': cue_id, 'bus': bus, 'status': status, 'waves': waves,
            'spatial': bool(cue['spatial']) and attenuation != '', 'attenuation': attenuation,
            'loop': bool(cue['loop']) or cue_id in LOOP_EDITS, 'max_instances': cue['max_instances'],
            'shuffle': cue['random'] != 'sequential', 'pitch_cents': cue['pitch_cents'],
            'volume_db': cue['volume_db'], 'caption': CAPTIONS.get(cue_id, ''),
            'caption_hero': cue_id in CAPTION_HERO, 'stinger': cue_id in STINGERS,
            'strike_ms': STRIKE_MS.get(cue_id, 0), 'sustain': SUSTAIN.get(cue_id),
            'needs': needs(cue, status, waves),
            'unbound': UNBOUND_CUES.get(cue_id, ''),
            'notes': cue['notes'],
        }
        if not waves and not entry['needs']:
            fail(f'{cue_id} has no waves and says nothing about what it needs')
        cues.append(entry)
    for added in ADDED_CUES:
        attenuation = added['attenuation']
        cues.append({
            'id': added['id'], 'bus': added['bus'], 'status': added['status'], 'waves': added['waves'],
            'spatial': attenuation != '', 'attenuation': attenuation, 'loop': added['loop'],
            'max_instances': added['max_instances'], 'shuffle': True,
            'pitch_cents': added.get('pitch_cents', [-40, 40]), 'volume_db': [-1.5, 0.0],
            'caption': added.get('caption', ''), 'caption_hero': False, 'stinger': False,
            'strike_ms': added.get('strike_ms', 0), 'sustain': None, 'needs': added.get('needs', ''),
            'unbound': '', 'notes': added['notes'],
        })
    known = {cue['id'] for cue in cues}
    unused = sorted(set(cc0) - known)
    if unused:
        fail(f'CC0 audio is made for unknown cues: {unused}')
    for table in (CAPTIONS, STRIKE_MS, SUSTAIN, UNBOUND_CUES, NEEDS, WAVE_EDITS, CC0_PLACEHOLDERS, STILL_WANTED):
        stale = sorted(set(table) - known)
        if stale:
            fail(f'edits name unknown cues: {stale}')
    return sorted(cues, key=lambda cue: cue['id'])


def classify_music(beat):
    task = beat['task']
    kind = beat['type']
    if kind == 'boss' or (kind == 'duel' and not task.get('sparring')):
        return 'boss'
    if kind == 'stealth_zone' or (kind == 'production_task' and task.get('guards')):
        return 'stealth'
    if task.get('sparring'):
        return 'exploration'
    if kind == 'combat_wave' or task.get('waves'):
        return 'combat'
    return 'exploration'


def sparring_weapon(beat):
    if not beat['task'].get('sparring') or beat['type'] != 'duel':
        return ''
    text = json.dumps(beat['params'])
    return 'fukuro_shinai' if 'shinai' in text or 'fukuro' in text else 'bokuto'


def beat_weather(beat, default):
    ext = beat.get('ext') or {}
    environment = ext.get('environment') or {}
    if environment.get('weather') in BEAT_WEATHER:
        return BEAT_WEATHER[environment['weather']]
    for change in ext.get('weather_events') or []:
        if change.get('set') in BEAT_WEATHER:
            return BEAT_WEATHER[change['set']]
    return default


def build_beats():
    beats = {}
    for chapter in range(1, 9):
        data = read(DATA / f'campaign/chapter_0{chapter}.json')
        places = PLACES[chapter]
        known = {place['id'] for place in data['places']}
        if set(places) != known:
            fail(f'chapter {chapter} places differ from the ambience table: '
                 f'missing {sorted(known - set(places))}, extra {sorted(set(places) - known)}')
        for beat in data['beats']:
            bed, weather, surface = places[beat['place']]
            environment = (beat.get('ext') or {}).get('environment') or {}
            beats[beat['id']] = {
                'chapter': chapter, 'place': beat['place'], 'music_id': beat['music'] or '',
                'state': classify_music(beat), 'sparring': sparring_weapon(beat), 'bed': bed,
                'weather': beat_weather(beat, weather), 'surface': surface,
                'thunder_s': environment.get('lightning_schedule_s', []),
            }
    return beats


def build_telegraphs():
    bosses = read(DATA / 'bosses.json')
    table = {}
    for boss in bosses['bosses']:
        for attack in boss['attacks']:
            special = SPECIAL_ATTACKS.get((boss['id'], attack['id']))
            if special:
                kind = special
            elif attack['kind'] in LOCK_KINDS_NONE or attack['telegraph'] == 'none':
                kind = 'none'
            elif attack['telegraph'] == 'cyan':
                kind = 'lock'
            else:
                kind = 'area' if attack['windup_ms'] >= AREA_WINDUP_MS else 'cleave'
            table[f"{boss['id']}/{attack['id']}"] = {'class': kind, 'windup_ms': attack['windup_ms']}
    # A rival duellist is a person, not a machine: his blows sound as his
    # blade (MeleeCommitted), never as a telegraph tone.
    for duel in bosses['duels']:
        for attack in duel['attacks']:
            table[f"{duel['id']}/{attack['id']}"] = {'class': 'none', 'windup_ms': attack['windup_ms']}
    enemies = {}
    for archetype in read(DATA / 'enemies.json')['archetypes']:
        for attack in archetype.get('attacks', []):
            enemies[attack['cue']] = {'class': 'lock' if attack['telegraph'] == 'cyan' else 'none',
                                      'windup_ms': attack['windup_ms']}
    difficulty = bosses['difficulty']
    return {'boss': table, 'enemy': enemies,
            'windup_permille': [difficulty['easy_windup_permille'], 1000, difficulty['hard_windup_permille']]}


def build():
    proposal = read(PROPOSAL)
    if proposal['sample_rate_hz'] != 48000:
        fail('the cue proposal changed its sample rate')
    return {
        'schema_version': SCHEMA,
        'source': 'scripts/audio/build_audio_data.py from Content/SourceArt/Audio/cues.proposed.json, '
                  'Content/Data/campaign, bosses.json and enemies.json',
        'sample_rate_hz': proposal['sample_rate_hz'],
        'buses': build_buses(proposal),
        'ducking': proposal['ducking'],
        'attenuation': build_attenuation(proposal),
        'cues': build_cues(proposal),
        'bindings': BINDINGS,
        'unbound_events': UNBOUND_EVENTS,
        'music': {
            'pieces': PIECES, 'states': STATES, 'alert_levels': ALERT_LEVELS,
            'crossfade_ms': {'into_alert': 250, 'out_of_alert': 2500, 'stems': 1200, 'piece': 1200},
            'stinger_duck_db': -6.0,
        },
        'beats': build_beats(),
        'maps': {str(map_id): {'bed': bed, 'weather': weather, 'surface': surface}
                 for map_id, (bed, weather, surface) in MAPS.items()},
        'weather': WEATHER,
        'footsteps': FOOTSTEPS,
        'horses': HORSES,
        'attached': ATTACHED,
        'telegraphs': build_telegraphs(),
    }


def render(data):
    return json.dumps(data, ensure_ascii=False, indent=1) + '\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n', 1)[0])
    parser.add_argument('--check', action='store_true', help='fail when the committed file differs')
    args = parser.parse_args()
    text = render(build())
    if args.check:
        if not OUT.is_file() or OUT.read_text(encoding='utf-8') != text:
            sys.exit(f'{OUT.relative_to(ROOT)} differs from a fresh build; run scripts/audio/build_audio_data.py')
        print(f'AUDIO_DATA_CURRENT: {OUT.relative_to(ROOT)}')
        return
    OUT.write_text(text, encoding='utf-8')
    data = json.loads(text)
    voiced = sum(1 for cue in data['cues'] if cue['waves'])
    print(f'Wrote {OUT.relative_to(ROOT)}: {len(data["cues"])} cues ({voiced} voiced), '
          f'{sum(len(rules) for rules in data["bindings"].values())} bindings in {len(data["bindings"])} families, '
          f'{len(data["beats"])} beats')


if __name__ == '__main__':
    main()
