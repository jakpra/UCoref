import os
import sys
import json

from xml.etree import ElementTree as ET

import curses

from ucca import convert as uconv
from ucca import constructions as uconst


filename = sys.argv[1]
out = sys.argv[2]


def print_passage(p, unit_id=None, parent_id=None):
    lines = []
    uline = []
    line = []
    unit = p.by_id(unit_id) if unit_id else None
    parent = p.by_id(parent_id) if parent_id else None
    ids = set(t.ID for t in unit.get_terminals(remotes=True)) if unit else set()
    non_remote_ids = set(t.ID for t in unit.get_terminals(remotes=False)) if unit else set()
    parent_ids = set(t.ID for t in parent.get_terminals(remotes=True)) if parent else set()
    first_sibling = None
    if unit and parent and unit.attrib.get('implicit'):
        first_sibling = min((t for t in parent.get_terminals() if t.ID not in ids), key=lambda x:x.position)
    for i, t in p.layer('0').pairs:
        if t.text == '\n':
            lines.append(''.join(line))
            uline = ''.join(uline)
            if uline.strip():
                lines.append(uline)
            line = []
            uline = []
            continue
        if t.ID in non_remote_ids:
            for c in t.text:
                line.append(c)
                uline.append('=')
        elif t.ID in ids:
            for c in t.text:
                line.append(c)
                uline.append('-')
        elif t.ID in parent_ids:
            if unit and unit.attrib.get('implicit') and t.ID == first_sibling.ID:
                line.extend(['I', 'M', 'P', ' '])
                uline.extend(['=', '=', '=', ' '])
            for c in t.text:
                line.append(c)
                uline.append('`')
        else:
            for c in t.text:
                line.append(c)
                uline.append(' ')
        line.append(' ')
        uline.append(' ')
    return lines


def get_sort_key(passage):
    last_position = len(str(passage))
    def sort_key(unit_pair):
        unit_id, annotation = unit_pair
        x = y = 0
        if passage.by_id(unit_id).end_position == -1:
            if 'parent' in annotation:
                x = passage.by_id(annotation['parent']).start_position
                y = -1
            else:
                x = last_position
                y = last_position
        else:
            x = passage.by_id(unit_id).start_position
            y = passage.by_id(unit_id).end_position * -1
        return (x, y)
    return sort_key



if filename.endswith('.json'):
    with open(filename) as f:
        p = uconv.from_json(f)
elif filename.endswith('.xml'):
    p = uconv.file2passage(filename)

sort_key = get_sort_key(p)
    
edges = uconst.extract_candidates(p, constructions=None, reference=None, reference_yield_tags=None, verbose=False)

m2a = {}  # mention candidate -> annotation

i = 0
for _e in edges.values():
    
    for _edge in _e:
        edge = _edge.edge
        if edge.tag in ('S', 'P'):
            if edge.parent in m2a:
                m2a[edge.parent.ID]['type'] = 'S'
                m2a[edge.parent.ID]['tag'] += '-Scene'
                m2a[edge.parent.ID]['require_annotation'] = True
            else:
                m2a[edge.parent.ID] = {'i': i, 'tag': 'Scene', 'type': 'S', 'require_annotation': True, 'index': -1}
                i += 1
                
        elif edge.tag in ('A', 'D', 'E', 'T', 'R', 'Q'):
            if edge.child in m2a:
                if 'parent' not in m2a[edge.child]:
                    m2a[edge.child.ID]['parent'] = edge.parent.ID
                if m2a[edge.child.ID]['tag'] == 'Scene':
                    m2a[edge.child.ID]['tag'] = edge.tag + '-Scene'
            else:
                m2a[edge.child.ID] = {'i': i, 'tag': edge.tag, 'type': None, 'index': -1,
                                        'parent': edge.parent.ID}
                i += 1
                
            if edge.tag == 'A':
                m2a[edge.child.ID]['require_annotation'] = True

tokens = {y.ID:y.text for x, y in p.layer('0').pairs}
words = [w.ID for w in p.layer('0').words if w.text.strip()]
units = [u.ID for u in p.layer('1').all]


ref2m = {}  # referent -> mentions
i2ref = []  # index -> referent
ref2i = {}  # referent -> index
d = {}
try:
    with open(out) as f:
        d = json.load(f)
        
    if 'units' in d:
        if units != d['units']:
            raise Exception('non-matching units in infile and outfile')
    if 'tokens' in d:
        if tokens != d['tokens']:
            raise Exception('non-matching tokens in infile and outfile')
            
except json.decoder.JSONDecodeError:
    pass
except FileNotFoundError:
    pass
except Exception as e:
    cmd = input(str(e) + '; continue? [y/N]')
    if cmd.lower() == 'y':
        pass
    else:
        sys.exit(0)

m2a.update(d.get('m2a', {}))
ref2m = d.get('ref2m', {})
for k in ref2m:
    ref2m[k] = set(ref2m[k])
i2ref = d.get('i2ref', [])
for i, ref in enumerate(i2ref):
    ref2i[ref] = i

with open('__x__', 'w') as disp:
    print( ' -----------------------', file=disp)
    print( ' UCCA Unit:      [   ]', file=disp)
    print( ' Head Unit:      [   ]', file=disp)
    print(f' UCCA Category:  [   ]', file=disp)
    print(f' Referent Index: [   ]', file=disp)
    print( ' -----------------------\n', file=disp)
    
    for line in print_passage(p):
        print(line, file=disp)

#with open('__x2__', 'w') as disp:
#with sys.stdout as disp:
print('\n##################################################################################################\n') #, file=disp)
for j, k in enumerate(i2ref):
    v = sorted(ref2m[k])
    print(j, '-', k, ':',
              ', '.join(('_'.join(t.text for t in p.by_id(uid).get_terminals(remotes=True))
              or ('IMP in ' + "_".join(t.text for t in p.by_id(m2a[uid]["parent"]).get_terminals(remotes=True))))
                        #+ ' (' + str(m2a[uid]['index']) + ')'
                        for uid in v)) #, file=disp)
print('\n##################################################################################################\n') #, file=disp)


candidates = [n for n, _ in sorted(m2a.items(), key=sort_key)]
index = 0  # index for mention unit candidates


print('[ENTER] start ', end='')
input()
cmd = 'start'

while cmd not in ('exit', 'quit'):

    #with open('__x2__', 'w') as disp:
    #with sys.stdout as disp:
    print('\n##################################################################################################\n') #, file=disp)
    for j, k in enumerate(i2ref):
        v = sorted(ref2m[k])
        print(j, '-', k, ':',
              ', '.join(('_'.join(t.text for t in p.by_id(uid).get_terminals(remotes=True))
              or ('IMP in ' + "_".join(t.text for t in p.by_id(m2a[uid]["parent"]).get_terminals(remotes=True))))
                        #+ ' (' + str(m2a[uid]['index']) + ')'
                        for uid in v)) #, file=disp)
    print('\n##################################################################################################\n') #, file=disp)

    unit_id = candidates[index]

    unit = p.by_id(unit_id)

    head = unit.process or unit.state or [str(n) for n in unit.centers]
    
    imp = unit.attrib.get('implicit')

    with open('__x__', 'w') as disp:
        print( ' -----------------------', file=disp)
        print( ' UCCA Unit:      [', str(unit) or 'IMPLICIT', ']', file=disp)
        print( ' Head Unit:      [', str(head) or 'IMPLICIT', ']', file=disp)
        print(f' UCCA Category:  [ {m2a[unit_id]["tag"]} ]', file=disp)
        print(f' Referent Index: [ {m2a[unit_id]["index"]} ]', file=disp)
        print( ' -----------------------\n', file=disp)

        parent_id = m2a[unit_id].get('parent')
        for line in print_passage(p, unit_id=unit_id, parent_id=parent_id):
            print(line, file=disp)
        
    # print(f'\n [ {m2a[unit_id]["type"]} ]\n')

    step = 1
    print('[ENTER] select referent for this mention: ', end='')
    cmd = input().split()
    # sys.stdout.flush()

    if ''.join(cmd) in ('exit', 'quit'):
        with open('__x__', 'w') as disp:
            print(end='')
        break

    if '/' in cmd:
        step = -1
        cmd.remove('/')

    if cmd:
        try:
            ref = int(cmd[0])
        except ValueError:  # string id
            ref = cmd[0]
            
            if ref == '-':
                
                if m2a[unit_id]['index'] != -1:
                    old_ref = i2ref[m2a[unit_id]['index']]
                    if unit_id in ref2m[old_ref]:
                        ref2m[old_ref].discard(unit_id)
                    if not ref2m[old_ref]:
                        ref2m.pop(old_ref)
                        i2ref.remove(old_ref)
                        for i, r in enumerate(i2ref):
                            ref2i[r] = i
                            for m in ref2m[r]:
                                m2a[m]['index'] = i
                                
                    m2a[unit_id]['index'] = -1
                
            elif ref in ref2m:
                ref2m[ref].add(unit_id)

                if ref2i[ref] != m2a[unit_id]['index']:
                    if m2a[unit_id]['index'] != -1:
                        old_ref = i2ref[m2a[unit_id]['index']]
                        if unit_id in ref2m[old_ref]:
                            ref2m[old_ref].discard(unit_id)
                        if not ref2m[old_ref]:
                            ref2m.pop(old_ref)
                            i2ref.remove(old_ref)
                            for i, r in enumerate(i2ref):
                                ref2i[r] = i
                                for m in ref2m[r]:
                                    m2a[m]['index'] = i
                                               
                    m2a[unit_id]['index'] = ref2i[ref]
                
            else:
                ref2m[ref] = {unit_id}
                ref2i[ref] = len(i2ref)
                i2ref.append(ref)
                
                if ref2i[ref] != m2a[unit_id]['index']:
                    if m2a[unit_id]['index'] != -1:
                        old_ref = i2ref[m2a[unit_id]['index']]
                        if unit_id in ref2m[old_ref]:
                            ref2m[old_ref].discard(unit_id)
                        if not ref2m[old_ref]:
                            ref2m.pop(old_ref)
                            i2ref.remove(old_ref)
                            for i, r in enumerate(i2ref):
                                ref2i[r] = i
                                for m in ref2m[r]:
                                    m2a[m]['index'] = i
                                               
                    m2a[unit_id]['index'] = ref2i[ref]
                
        else:  # index
            if ref < len(i2ref) and ref >= 0:
                ref = i2ref[ref]
                ref2m[ref].add(unit_id)
                
                if ref2i[ref] != m2a[unit_id]['index']:
                    if m2a[unit_id]['index'] != -1:
                        old_ref = i2ref[m2a[unit_id]['index']]
                        if unit_id in ref2m[old_ref]:
                            ref2m[old_ref].discard(unit_id)
                        if not ref2m[old_ref]:
                            ref2m.pop(old_ref)
                            i2ref.remove(old_ref)
                            for i, r in enumerate(i2ref):
                                ref2i[r] = i
                                for m in ref2m[r]:
                                    m2a[m]['index'] = i
                                               
                    m2a[unit_id]['index'] = ref2i[ref]
                
            else:
                ref = '_'.join(t.text for t in unit.get_terminals(remotes=True)) or ('IMP_in_' + "_".join(t.text for t in p.by_id(m2a[unit_id]["parent"]).get_terminals(remotes=True)))
                
                ref2m[ref] = {unit_id}
                ref2i[ref] = len(i2ref)
                i2ref.append(ref)

                if ref2i[ref] != m2a[unit_id]['index']:
                    if m2a[unit_id]['index'] != -1:
                        old_ref = i2ref[m2a[unit_id]['index']]
                        if unit_id in ref2m[old_ref]:
                            ref2m[old_ref].discard(unit_id)
                        if not ref2m[old_ref]:
                            ref2m.pop(old_ref)
                            i2ref.remove(old_ref)
                            for i, r in enumerate(i2ref):
                                ref2i[r] = i
                                for m in ref2m[r]:
                                    m2a[m]['index'] = i
                                               
                    m2a[unit_id]['index'] = ref2i[ref]


        os.system(f'cp {out} {out}.bak')
        try:
            with open(out, 'w') as f:
                d = {}
                d['tokens'] = tokens
                d['words'] = words
                d['units'] = units
                d['m2a'] = m2a
                _ref2m = {}
                for k in ref2m:
                    _ref2m[k] = sorted(ref2m[k])
                d['ref2m'] = _ref2m
                d['i2ref'] = i2ref
                json.dump(d, f, indent=2)
        except _ as e:
            os.system('cp {out}.bak {out}')
            raise IOError(e)
        

    index += step
    if index < 0:
        index += len(candidates)
    elif index >= len(candidates):
        index -= len(candidates)
