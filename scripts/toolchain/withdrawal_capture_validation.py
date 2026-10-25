"""Validate live retreat observations; original pixels still need visual review."""
import math

SCHEMA = 'sora-arena.withdrawal-capture.v2'
SCOPE = ('prepared checkpoint/cameras; combat frozen during real defense timer; '
         'live survivor navigation, three bilingual HUD frames and one HUD-hidden arrival detail; '
         'not ordinary defense or art acceptance')
PHASES = ('retreat-bark', 'walking', 'gate-clear', 'arrival-detail')


def number(row, key, integer=False):
    v = row.get(key)
    try:
        valid = type(v) in (int, float) and math.isfinite(v)
    except OverflowError:
        valid = False
    if not valid or (integer and (v < 0 or v > 2**53-1 or int(v) != v)):
        raise ValueError(f'invalid withdrawal observation {key}')
    return v


def vector(v, size):
    if not isinstance(v, list) or len(v) != size:
        raise ValueError('invalid withdrawal vector')
    return [number({'v': part}, 'v') for part in v]


def verify_sequence(data, filenames, width, height):
    if not isinstance(data, dict) or data.get('schema') != SCHEMA or data.get('scope') != SCOPE:
        raise ValueError('withdrawal schema/scope mismatch')
    for key in ('passed', 'ordinary_clock', 'profiles_preserved', 'mappings_preserved', 'temporary_slot_deleted'):
        if data.get(key) is not True:
            raise ValueError(f'withdrawal did not establish {key}')
    if vector(data.get('viewport'), 2) != [width, height] or (width, height) not in ((1280,720), (1920,1080)):
        raise ValueError('withdrawal viewport mismatch')
    rows = data.get('frames')
    expected = [p+'.png' for p in PHASES]
    if filenames != expected or not isinstance(rows, list) or len(rows) != 4:
        raise ValueError('withdrawal needs four unique original phases in order')
    if number(data, 'completions', True) != 1 or number(data, 'survivor_shots', True) != 0:
        raise ValueError('withdrawal completion/shots disagree')
    if number(data, 'down_before', True) != number(data, 'down_at_completion', True):
        raise ValueError('withdrawal invented defeat credit')
    if (number(data, 'defense_ms', True) < 150000 or number(data, 'defense_world_s') < 149
            or number(data, 'defense_wall_s') < 149 or number(data, 'walked_cm') < 1000
            or number(data, 'gate_clear_world_s') < 2.5 or number(data, 'gate_clear_wall_s') < 2.4):
        raise ValueError('withdrawal has compressed clocks/missing movement or call')
    previous = [-1, -1, -1]
    identities = None
    positions = []
    for index, (phase, row) in enumerate(zip(PHASES, rows)):
        if not isinstance(row, dict) or row.get('phase') != phase or row.get('file') != expected[index]:
            raise ValueError('withdrawal phase/filename mismatch')
        if row.get('paused') is not False or row.get('hud_drawn') is not (index < 3) or row.get('english') is not True:
            raise ValueError('withdrawal requires three live bilingual HUD frames and one HUD-hidden detail')
        current = [number(row, 'request_frame', True), number(row, 'world_s'), number(row, 'wall_s')]
        if (number(row, 'processed_frame', True) != current[0] or any(a <= b for a,b in zip(current,previous))
                or number(row, 'defense_ms', True) != data['defense_ms']):
            raise ValueError('withdrawal frame identity/order/clock mismatch')
        previous = current
        camera = vector(row.get('camera'), 3)
        rotation = vector(row.get('camera_rotation'), 3)
        eye, pitch, yaw, fov = (([-500,-3400,1900],math.degrees(math.atan2(-1800,3400)),90,75) if index < 3
                               else ([-2220,0,1200],math.degrees(math.atan2(-1110,80)),180,45))
        angle_errors = [abs((actual-wanted+180)%360-180) for actual,wanted in zip(rotation,[pitch,yaw,0])]
        if math.dist(camera,eye) > .01 or max(angle_errors) > .001 or abs(number(row,'camera_fov')-fov) > .001:
            raise ValueError('withdrawal rendered camera differs from its required view')
        if index == 0 and row.get('cue') != 'ch02.b02.enforcer.009':
            raise ValueError('retreat original lacks its real bark')
        if index >= 2 and row.get('cue') != 'ch02.b06.kohagi.006':
            raise ValueError('arrival original lacks the real gate-clear call')
        if number(row, 'walked_cm') < (1000 if index else 0):
            raise ValueError('withdrawal did not walk its route')
        people = row.get('survivors')
        if not isinstance(people, list) or len(people) != 6 or any(not isinstance(p,dict) for p in people):
            raise ValueError('withdrawal lacks six actual survivors')
        names = [p.get('actor') for p in people]
        if any(not isinstance(n,str) or not n for n in names) or len(set(names)) != 6:
            raise ValueError('withdrawal survivor identities are invalid/duplicate')
        if identities is not None and names != identities:
            raise ValueError('withdrawal swapped its survivors')
        identities = names
        at = []
        for person in people:
            pos = vector(person.get('position'),3); screen = vector(person.get('screen'),2)
            at.append(pos)
            if not (25 <= screen[0] <= width-25 and 60 <= screen[1] <= height-100):
                raise ValueError('withdrawal survivor is outside the view')
            if type(person.get('at_approach')) is not bool:
                raise ValueError('invalid approach observation')
            if index >= 2 and (person['at_approach'] is not True or math.dist(pos[:2],[-2300,0]) > 220
                    or abs(number(person,'feet_z')) > 30 or person.get('grounded') is not True):
                raise ValueError('withdrawal call preceded grounded physical arrival')
        positions.append(at)
    if sum(math.dist(a[:2],b[:2]) for a,b in zip(positions[0],positions[1])) < 500:
        raise ValueError('walking originals show no actual survivor displacement')
