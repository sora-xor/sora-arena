"""Bind Collatera's authored mechanics to the existing bridge gameplay hall."""
import math


def place_bridge(beats, records, zones, fail):
    for beat, record in zip(beats, records):
        if beat['id'] != 'ch07.b13':
            continue
        tables = beat['ext'].get('pattern_tables', {})
        p2, p3 = tables.get('collatera_p2_margin_call', {}), tables.get('collatera_p3_sabre', {})
        slides = [a for a in p2.get('attacks', []) if a.get('id') == 'slide_props']
        def exact(value, expected):
            return type(value) in (int, float) and math.isfinite(value) and value == expected
        arena = p2.get('arena', {})
        if (beat['place'] != 'pl_bridge' or len(slides) != 1 or
                not all(exact(arena.get(k), v) for k, v in
                        [('list_deg', 10), ('uphill_speed_mult', .85), ('downhill_speed_mult', 1.1)]) or
                not exact(p3.get('arena', {}).get('list_deg'), 10)):
            fail(beat['id'], 'Collatera requires the authored phase-two/three deck list')
        slide = slides[0]
        if (not all(exact(slide.get(k), v) for k, v in
                    [('every_s', 6), ('windup_ms', 700), ('damage', 30), ('knockdown_s', .6)]) or
                slide.get('direction') != 'port' or slide.get('telegraph') != 'scrape_audio_and_wobble'):
            fail(beat['id'], 'Collatera requires the authored sliding-prop warning and contact damage')
        zone = zones[record['zone']]
        if zone['place'] != 'pl_bridge' or zone['form'] != 'hall':
            fail(beat['id'], 'deck motion must bind only the actual bridge zone')
        x0, y0, x1, y1 = zone['rect']
        if x1-x0 != 5600 or y1-y0 != 4200:
            fail(beat['id'], 'bridge prop lanes require the current 56 by 42 metre proxy hall')
        center = [(x0+x1)//2, (y0+y1)//2]
        # Separate lanes in the current proxy hall, clear of its fixed cover
        # and entry/exit/helm. Six chairs and four pods are authored (§3).
        record['bridge'] = dict(center=center, list_deg=10, uphill_permille=850,
                                downhill_permille=1100, every_ms=6000, warning_ms=700,
                                damage=30, stagger_ms=600, chairs=6, pods=4,
                                port=[0, -1])

        margins = [a for a in p2.get('attacks', []) if a.get('id') == 'margin_call']
        if len(margins) != 1 or not all(exact(margins[0].get(k), v) for k, v in
                [('every_s', 7), ('windup_ms', 1500), ('targets', 3), ('damage', 60),
                 ('cover_hits_to_destroy', 2), ('max_cover_destroyed', 6)]) or (
                margins[0].get('telegraph') != 'amber_ring_250cm' or
                margins[0].get('targeting') != "cover nearest the player, else the player's position"):
            fail(beat['id'], 'Collatera requires the authored margin-call cover contract')
        # Functional console bodies in the current flat hall. This is not the
        # authored tiered amphitheatre. Preserve the centre traversal, outer
        # sliding lanes, entry, exit, and helm footprint.
        zone['cover'][:] = [[center[0]+x, center[1]+y, 80, 300, 110]
                            for x in (-1000, 0, 1000) for y in (-1550, -900, -300, 400, 1400)]
        record['bridge']['margin'] = dict(consoles=15, hits_to_destroy=2, max_destroyed=6,
                                          targets=3, every_ms=7000, warning_ms=1500,
                                          radius_cm=250, damage=60, linger_ms=6000)
