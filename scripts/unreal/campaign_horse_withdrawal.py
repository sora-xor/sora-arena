"""Current ch02.b06 outro: withdraw to the navigable west-gate approach."""
from campaign_pods import same

EVENT = 'event:horse_defense_withdrawal'
BARK = 'ch02.b02.enforcer.009'
GATE_CLEAR = 'ch02.b06.kohagi.006'
AUTHORING = dict(muster='ps_gate_yard_start', arrival_cm=220, pace_permille=750,
                 event=EVENT, bark=BARK)
GOAL = [-2300, 0, 0]
SLOTS = [[-130,-100],[-130,100],[0,-100],[0,100],[130,-100],[130,100]]


def contract(beat, record, layout):
    if (beat['id'] != 'ch02.b06' or beat['place'] != 'pl_estate_night' or
            not same(beat['ext']['withdrawal'], AUTHORING) or record['zone'] != -1 or
            not same(record['height_cm'], 0) or beat['task']['goal'] != 'survive' or
            not same(beat['task']['duration_ms'], 150000)):
        raise ValueError('horse withdrawal requires its authored defense and current contract')
    points = [p for p in layout['points'] if p['id'] == AUTHORING['muster']]
    if (len(points) != 1 or points[0]['frame'] != 'pl_estate_night' or
            points[0]['place'] != 'pl_estate_night' or not same(points[0]['positions_cm'], [GOAL])):
        raise ValueError('horse withdrawal must use the navigable named gate approach')
    return dict(**AUTHORING, floor_cm=GOAL, floor_tolerance_cm=30,
                slots_cm=SLOTS, slot_acceptance_cm=30,
                completion='arrived_survivors_then_finished_gate_clear')


def place_horse_withdrawal(beats, records, layout, fail):
    for beat, record in zip(beats, records):
        if beat['id'] == 'ch02.b06':
            try:
                record['horse_withdrawal'] = contract(beat, record, layout)
            except (KeyError, TypeError, ValueError) as error:
                fail(beat['id'], str(error))


def horse_withdrawal_valid(chapter):
    try:
        if len(chapter['beats']) != len(chapter['space']['beats']):
            return False
        for beat, record in zip(chapter['beats'], chapter['space']['beats']):
            if record['beat'] != beat['id']:
                return False
            if beat['id'] == 'ch02.b06':
                if not same(record['horse_withdrawal'], contract(beat, record, chapter['layout'])):
                    return False
                for event, line in ((EVENT, BARK), ('beat_complete', GATE_CLEAR)):
                    triggers = [t for t in chapter['triggers'] if t['beat'] == beat['id'] and t['on'] == event]
                    if (len(triggers) != 1 or triggers[0]['lines'] != [line] or
                            triggers[0]['mode'] != 'ambient' or triggers[0]['repeatable'] is not False):
                        return False
            elif 'horse_withdrawal' in record or 'withdrawal' in beat['ext']:
                return False
        return True
    except (KeyError, TypeError, ValueError):
        return False
