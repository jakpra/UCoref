import sys
import json

from ucca import convert as uconv
from ucca import layer1 as ul1

'''
python %s "parachute_1_orig.json parachute_2_orig.json" "whow_parachute_1_orig.xml whow_parachute_2_orig.xml"
'''

def handle_head_and_return_if_special(head, parent_id, multi_head=False, nested=False):
    if not ((head.fparent.ID == parent_id) or head.ID == parent_id or nested): # remote head
        if head.ID in m2a:
            m2a[head.ID]['remote'] = True
        m2a[parent_id]['is_own_head'] = True
        return 1

    if head.centers:  # nested center: descend to deepest
        if head.ID in m2a:
            m2a[head.ID]['nested'] = True
        for c in head.centers:
            is_special = handle_head_and_return_if_special(c, head.ID if multi_head else parent_id, multi_head=len(head.centers)>1, nested=True)
            if is_special:
                pass
        if not multi_head:
            return 2

    toks = list(set([tok_ids.index(t.ID) for t in p.by_id(head.ID).get_terminals()]))

    if ul1.EdgeTags.Participant in head.ftags and (ul1.EdgeTags.State in head.ftags or ul1.EdgeTags.Process in head.ftags): # relational noun (S+A, P+A)
        '''
        remove this mention
        '''
        ...
        handle_rel_noun(head)
        return 3

    if not toks: # implicit
        m2a[parent_id]['is_own_head'] = True
        if head.ID in m2a:
            m2a[head.ID]['implicit'] = True
        return 4

    if head.is_scene(): # relational noun
        '''
        remove scene version of mention, make coreferring with containing unit
        '''
        ...
        # return True
        if head.ID in mentions:
            ref = ann['i2ref'][m2a[head.ID]['index']]
            referents[ref].remove(head.ID)
            if not referents[ref]:
                referents.pop(ref)
            m2a.pop(head.ID)


    # none of the above
    if multi_head or head.ID == parent_id:
        if head.ID in mentions and head.ID in m2a: # for multi-head units, heads should NOT corefer with unit, except for certain partitive constructions
            # assert head.ID not in referents[ann['i2ref'][m2a[m]['index']]], (head.ID, m, mentions[head.ID], mentions[m])
            head_ref = referents[ann['i2ref'][m2a[head.ID]['index']]]
            pass
        else:
            m2a[head.ID] = {'i': len(m2a), 'tag': p.by_id(parent_id).ftag, 'type': None, 'parent': parent_id}
            mentions_to_add[head.ID] = toks
        m2a[head.ID]['is_own_head'] = True
        m2a[parent_id]['is_own_head'] = True

    elif parent_id in mentions:
        m2a[parent_id]['head'] = head.ID
        if head.ID in mentions and head.ID in m2a:  # if single head is already a mention, ensure that it corefers with unit
            head_ref = referents[ann['i2ref'][m2a[head.ID]['index']]]
            parent_ref = referents[ann['i2ref'][m2a[parent_id]['index']]]
            assert head.ID in parent_ref, (head.ID, parent_id, multi_head, nested, list(map(tokens.__getitem__, toks)), list(map(tokens.__getitem__, mentions[parent_id])), mentions[head.ID], mentions[parent_id], head_ref, parent_ref)
        else:
            m2a[head.ID] = m2a[parent_id].copy()
            if 'index' not in m2a[parent_id]:
                m2a[parent_id]['index'] = len(ann['i2ref'])
            m2a[head.ID].update({'i': len(m2a), 'parent': parent_id, 'require_annotation': False, 'index': m2a[parent_id]['index']})
            mentions_to_add[head.ID] = toks

        m2a[head.ID]['is_head_of_parent'] = True

    return 0


def handle_rel_noun(unit):
    if unit.ID in m2a:
        m2a[unit.ID]['rel_noun'] = True
    ...
    return


ucca_ref = sys.argv[1]
ucca_pass = sys.argv[2]
min_span = 'min' in sys.argv
max_span = 'max' in sys.argv
keep_imp = 'imp' in sys.argv

global ann, p, tok_ids, tokens, m2a, mentions_to_add, mentions, referents

with open(ucca_ref) as f:
    ann = json.load(f)

p = uconv.file2passage(ucca_pass)

tok_ids = sorted([t for t, w in ann['tokens'].items() if w.strip()], key=lambda x:p.by_id(x).position)
tokens = [ann['tokens'][t] for t in tok_ids]

mentions = {unit: list(set([tok_ids.index(t.ID) for t in p.by_id(unit).get_terminals()])) for unit, a in ann['m2a'].items() if a['index'] != -1}

m2a = ann['m2a']
referents = ann['ref2m']

mentions_to_add = {}
mentions_to_remove = {}

for m in mentions.keys():
    unit = p.by_id(m)
    if unit.is_scene():
        heads = [unit.state or unit.process]
        m2a[m].update({'type': 'S'})
    else:
        heads = unit.centers or [unit]

    for head in heads:
        is_special = handle_head_and_return_if_special(head, m, multi_head=len(heads)>1)
#        if head.ID in ("1.6", "1.16", "1.27"):
#            print(head.ID, is_special, list(map(tokens.__getitem__, mentions[head.ID])))
        #if is_special:
        #    pass

for m, toks in mentions_to_add.items():
    # print(m, toks, m2a[m])
    mentions[m] = toks
    if 'index' in m2a[m] and m2a[m]['index'] < len(ann['i2ref']):
        referents[ann['i2ref'][m2a[m]['index']]].append(m)
    else:
        ref = f'HEAD_{m}_m'
        referents[ref] = [m]
        m2a[m]['index'] = len(ann['i2ref'])
        ann['i2ref'].append(ref)


print('checking sanity...')
for unit in p.layer("1").all:
    uid = unit.ID
    assert (uid in mentions.keys()) == any(uid in ref for ref in referents.values()), (uid, mentions[uid], [ref for ref in referents.values() if uid in ref]) # , referents.values())
    if unit.ftag in {ul1.EdgeTags.Center, ul1.EdgeTags.Process, ul1.EdgeTags.State}:
        if uid in mentions.keys() and m2a[uid].get('is_head_of_parent'):
            pid = m2a[uid]['parent']
            assert pid in m2a
            assert pid in mentions
            assert len([ref for ref in referents.values() if pid in ref]) == 1

    if unit.centers or unit.process or unit.state:
        if uid in mentions.keys() and m2a[uid].get('head'):
            hid = m2a[uid].get('head')
            assert hid in m2a
            assert hid in mentions
            assert len([ref for ref in referents.values() if hid in ref]) == 1

print('looks sane')


filtered_mentions = {}
filtered_m2a = {}

if min_span:
    for m in mentions:
        if not (m2a[m].get('rel_noun')) and (keep_imp or not m2a[m].get('implicit')) and (m2a[m].get('is_own_head') or m2a[m].get('is_head_of_parent')):
#         if not (m2a[m].get('rel_noun')) and (m2a[m].get('is_own_head') or m2a[m].get('is_head_of_parent')):
            filtered_m2a[m] = m2a[m]
            filtered_mentions[m] = mentions[m]

if max_span:
    for m in mentions:
        if (not m2a[m].get('rel_noun')) and (keep_imp or not m2a[m].get('implicit')) and (not m2a[m].get('is_head_of_parent')):
#         if not (m2a[m].get('rel_noun') or m2a[m].get('is_head_of_parent')):
            filtered_m2a[m] = m2a[m]
            filtered_mentions[m] = mentions[m]


filtered_referents = {}
for k, v in referents.items():
    _v = [m for m in v if m in filtered_mentions]
    if _v:
        filtered_referents[k] = _v

minmax = ('min' if min_span else '') + ('max' if max_span else '')
if minmax:
    minmax += '.'

_imp = ('imp' if keep_imp else '')
if _imp:
    _imp += '.'

with open(f'{ucca_ref}.ucoref.' + minmax + _imp + 'json', 'w') as f:
    d = {}
    d['tokens'] = tokens
    d['mentions'] = filtered_mentions if min_span or max_span else mentions
    d['m2a'] = filtered_m2a if min_span or max_span else m2a
    d['referents'] = filtered_referents if min_span or max_span else referents
    json.dump(d, f, indent=2)
