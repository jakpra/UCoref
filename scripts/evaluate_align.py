import sys
import json

from collections import Counter
from operator import itemgetter

file1 = sys.argv[1]
file2 = sys.argv[2]

mu_m = float(sys.argv[3])
mu_r = float(sys.argv[4])
no_singl = 'nos' in sys.argv

'''
python %s file1.ucoref.json file2.ucoref.json"
'''

def f1(ol, a, b):
    p = ol/a
    r = ol/b
    return 0 if p+r == 0 else (2*p*r)/(p+r)

def dice(ol, a, b):
    return (2 * ol) / (a+b)

_score = lambda ol, a, b: dice(ol, a,b)
# mu = 0.0
# eta = 0.1


# mu = int((mu * 10) - 1)
# eta = int(eta * -10)

with open(file1) as f:
    a = json.load(f)

with open(file2) as f:
    b = json.load(f)


a_tok = len(a['tokens'])
b_tok = len(b['tokens'])
assert a_tok == b_tok, f'{a_tok} != {b_tok}'

exact_m = 0
imp_a = 0
imp_b = 0
remote_a = 0
remote_b = 0
partial_m_a = 0
partial_m_b = 0
alignments_ma = alignments_m = {}
alignments_mb = {}
alignments_m_by_a_tag = Counter()
alignments_m_by_b_tag = Counter()

for mention_b, tokens_b in b['mentions'].items():
    if not tokens_b:
        imp_b += 1
    if b['m2a'][mention_b].get('remote'):
        remote_b += 1

# mention alignment
scores_m = {}
for ma, ta in a['mentions'].items():
    if not ta:
        imp_a += 1
    if a['m2a'][ma].get('remote'):
        remote_a += 1
    for mb, tb in b['mentions'].items():
        ol = [t for t in ta if t in tb]
        if ol:
            scores_m[ma, mb] = _score(len(ol), len(ta), len(tb))

_scores_m = sorted(scores_m.items(), key=itemgetter(1), reverse=True)

for (ma, mb), s in _scores_m:
    if s < mu_m: break
    if ma not in alignments_ma and mb not in alignments_mb:
        alignments_ma[ma] = mb
        alignments_mb[mb] = ma
#        alignments_m_by_a_tag[a['m2a'][ma]['tag']] += 1
#        alignments_m_by_b_tag[b['m2a'][mb]['tag']] += 1
        if s == 1.0:
            exact_m += 1

print('MENTIONS\n')
for m_a, m_b in alignments_m.items():
    print(' '.join([a['tokens'][i] for i in sorted(a['mentions'][m_a])]))
    print(' '.join([b['tokens'][i] for i in sorted(b['mentions'][m_b])]))
    print(scores_m[m_a, m_b])
    print()

n = 5
print('* unaligned A\n    top n B *\n')
for m_a in a['mentions']:
    i = n
    if m_a not in alignments_ma:
        print(' '.join([a['tokens'][i] for i in sorted(a['mentions'][m_a])]))
        for (_ma, _mb), s in _scores_m:
            if i <= 0: break
            if _ma == m_a:
                print(f'    {s} ' + ' '.join([b['tokens'][i] for i in sorted(b['mentions'][_mb])]))
                i -= 1
        print()

print()

print('* unaligned B\n    top n A *\n')
for m_b in b['mentions']:
    i = n
    if m_b not in alignments_mb:
        print(' '.join([b['tokens'][i] for i in sorted(b['mentions'][m_b])]))
        for (_ma, _mb), s in _scores_m:
            if i <= 0: break
            if _mb == m_b:
                print(f'    {s} ' + ' '.join([a['tokens'][i] for i in sorted(a['mentions'][_ma])]))
                i -= 1
        print()

print()



if no_singl:
    a_referents = {r: m for r, m in a['referents'].items() if len(m)>1}
    b_referents = {r: m for r, m in b['referents'].items() if len(m)>1}
else:
    a_referents = a['referents']
    b_referents = b['referents']

a_refs = list(a_referents.values())
b_refs = list(b_referents.values())

print(a_referents, a_refs)
print(b_referents, b_refs)

exact_r = 0
singl_a = 0
singl_b = 0
imp_singl_a = 0
imp_singl_b = 0
rem_singl_a = 0
rem_singl_b = 0
partial_r_a = 0
partial_r_b = 0
alignments_ra = alignments_r = {}
alignments_rb = {}
alignments_r_by_a_type = Counter()
alignments_r_by_b_type = Counter()

equiv = {}
equiv['Scene'] = 'Event'
equiv['D'] = 'Event'
equiv['T'] = 'Time'
equiv['event'] = 'Event'
equiv['abstract'] = 'Event'
equiv['time'] = 'Time'
equiv['EVENT'] = 'Event'
equiv['TIMEX3'] = 'Time'

#_b_referents = {}
for referent_b, mentions_b in b_referents.items():
    b_referents[referent_b] = [str(m) for m in mentions_b]
    if len(mentions_b) == 1:
        singl_b += 1
        if not b['mentions'][str(mentions_b[0])]:
            imp_singl_b += 1
        if b['m2a'][str(mentions_b[0])].get('remote'):
            rem_singl_b += 1

# referent alignment
scores_r = {}
for ra, ma in a_referents.items():
    if len(ma) == 1:
        singl_a += 1
        if not a['mentions'][str(ma[0])]:
            imp_singl_a += 1
        if a['m2a'][str(ma[0])].get('remote'):
            rem_singl_a += 1
    for rb, mb in b_referents.items():
        ol = [m for m in ma if str(alignments_ma.get(str(m))) in mb]
        if ol:
#            print('ok1')
            scores_r[ra, rb] = _score(len(ol), len(ma), len(mb))
#        else:
#            assert False, (ma, mb, [alignments_ma.get(str(m)) for m in ma])

for (ra, rb), s in sorted(scores_r.items(), key=itemgetter(1), reverse=True):
    if s < mu_r: break
    if ra not in alignments_ra and rb not in alignments_rb:
#        print('ok2')
        alignments_ra[ra] = rb
        alignments_rb[rb] = ra
#        a_type = 'Entity'
#        b_type = 'Entity'
#        for ref_type in equiv.values():
#            if any(equiv.get(a.get('m2a', {}).get(m)['tag']) == ref_type for m in mentions_a):
#                a_type = ref_type
#            if any(equiv.get(b.get('m2a', {}).get(m)['tag']) == ref_type for m in aligned[1]):
#                b_type = ref_type
#        alignments_r_by_a_type[a_type] += 1
#        alignments_r_by_b_type[b_type] += 1
        if s == 1.0:
            exact_r += 1

print('\nREFERENTS\n')
for r_a, r_b in alignments_r.items():
    print(', '.join(['_'.join([a['tokens'][i] for i in sorted(a['mentions'][str(m_a)])]) for m_a in a_referents[r_a]]))
    print(', '.join(['_'.join([b['tokens'][i] for i in sorted(b['mentions'][str(m_b)])]) for m_b in b_referents[r_b]]))
    print()



def prf(tp, l_a, l_b):
    r = tp/l_a
    p = tp/l_b
    return (p, r, 0 if not p+r else (2*p*r)/(p+r))

def m2t(doc, aligned_doc=None, align={}):
    assert not align or aligned_doc
    return lambda m: sorted(aligned_doc['mentions'][str(align[m])] if m in align else doc['mentions'][str(m)])



def ceaf_m(a_referents, b_referents):
    #_a_refs = {ra: [alignments_ma[m] for m in ma] for ra, ma in a_refs.items()}
    #_b_refs = {rb: list(map(m2t(b, a, alignments_mb), mb)) for rb, mb in b_refs.items()}
    tp = sum(len([m for m in a_referents[ra] if alignments_ma.get(m, m) in b_referents[rb]]) for ra, rb in alignments_r.items() if (ra in b_referents and rb in b_referents))
    l_a = sum(len(ma) for _, ma in a_referents.items())
    l_b = sum(len(mb) for _, mb in b_referents.items())
    return prf(tp, l_a, l_b)

def ceaf_e(a_referents, b_referents):
    tp = sum(scores_r[ra, alignments_ra[ra]] for ra, rb in alignments_r.items() if (ra in a_referents and rb in b_referents))
    l_a = len(a_referents)
    l_b = len(b_referents)
    return prf(tp, l_a, l_b)


def b_cub(a_refs, b_refs):
    l_a = sum(len(ra) for ra in a_refs)
    l_b = sum(len(rb) for rb in b_refs)
    num_r = num_p = 0
    for ra in a_refs:
        _ra = [alignments_ma.get(m, m) for m in ra]
        for rb in b_refs:
            #_rb = list(map(m2t(b), rb))
#            print(_ra)
#            print(_rb)
            ol_sq = len([m for m in _ra if m in rb])**2
            num_r += ol_sq/len(ra)
            num_p += ol_sq/len(rb)
#        print()
    r = num_r/l_a
    p = num_p/l_b
    return (p, r, 0 if not p+r else (2*p*r)/(p+r))

def partition(part, reference):
    _reference = reference.copy()
    partitions = []
    for r in part:
        p = []
        for m in r:
            if m in _reference:
                _reference.remove(m)
                p.append(m)
        if p:
            partitions.append(p)
        if not _reference: break
    for m in _reference:
        partitions.append([m])
    return partitions

def muc(a_refs, b_refs):
    l_a = sum(len(ra)-1 for ra in a_refs)
    l_b = sum(len(rb)-1 for rb in b_refs)
    _a_refs = [[alignments_ma.get(m, m) for m in ra] for ra in a_refs]
    #_b_refs = [list(map()) for rb in b_refs]
    r_num = p_num = 0
    for ra in _a_refs:
        r_num += len(ra) - len(partition(b_refs, ra))
    for rb in b_refs:
        p_num += len(rb) - len(partition(_a_refs, rb))
    r = r_num / l_a
    p = p_num / l_b
    return (p, r, 0 if not p+r else (2*p*r)/(p+r))

def conll(a_refs, b_refs):
    c = ceaf_e(a_referents, b_referents)
    m = muc(a_refs, b_refs)
    b = b_cub(a_refs, b_refs)
    return(0, 0, (c[2]+m[2]+b[2])/3)

ex_m = exact_m
al_m = len(alignments_m)
a_m = len(a['mentions'])
b_m = len(b['mentions'])

print()

print('''\\begin{table}[ht]\centering
\\begin{tabular}{|l|r|c|c|}
\\hline
\\textbf{mentions} & \\# & \\% exact & \\% fuzzy \\\\
\\hline''')
#print('\nmentions')
print('exact', ex_m, '-', '-', sep=' & ', end=' \\\\\n')
print('fuzzy', al_m, f'{ex_m*100/al_m:.1f}', '-', sep=' & ', end=' \\\\\\hline\n')
print('A', a_m, f'{ex_m*100/a_m:.1f}', f'{al_m*100/a_m:.1f}', sep=' & ', end=' \\\\\n')
print('B', b_m, f'{ex_m*100/b_m:.1f}', f'{al_m*100/b_m:.1f}', sep=' & ', end=' \\\\\\hline\n')
print('F1', '', f'{f1(ex_m, a_m, b_m)*100:.1f}', f'{f1(al_m, a_m, b_m)*100:.1f}', sep=' & ', end=' \\\\\n')


ex_r = exact_r
al_r = len(alignments_r)
a_r = len(a_referents)
b_r = len(b_referents)
print('''\\hline
\\textbf{referents}  \\\\
\\hline''')
#print('\nreferents')
print('exact', ex_r, '-', '-', sep=' & ', end=' \\\\\n')
print('fuzzy', al_r, f'{0 if not al_r else ex_r*100/al_r:.1f}', '-', sep=' & ', end=' \\\\\\hline\n')
print('A', a_r, f'{ex_r*100/a_r:.1f}', f'{al_r*100/a_r:.1f}', sep=' & ', end=' \\\\\n')
print('B', b_r, f'{ex_r*100/b_r:.1f}', f'{al_r*100/b_r:.1f}', sep=' & ', end=' \\\\\\hline\n')
print('F1', '', f'{f1(ex_r, a_r, b_r)*100:.1f}', f'{f1(al_r, a_r, b_r)*100:.1f}', sep=' & ', end=' \\\\\n')
print('''\\hline
\end{tabular}
\caption{\label{tab:}}
\end{table}''')

print()

print('fuzzy m A alignments by type', alignments_m_by_a_tag)
print('fuzzy m B alignments by type', alignments_m_by_b_tag)
print('fuzzy r A alignments by type', alignments_r_by_a_type)
print('fuzzy r B alignments by type', alignments_r_by_b_type)

print('IMP A', imp_a)
print('IMP B', imp_b)
print('REMOTE A', remote_a)
print('REMOTE B', remote_b)
print('singletons A', singl_a)
print('singletons B', singl_b)
print('imp singletons A', imp_singl_a)
print('imp singletons B', imp_singl_b)
print('singleton remote A', rem_singl_a)
print('singleton remote B', rem_singl_b)

print('CEAF_m P/R/F', ceaf_m(a_referents, b_referents))
print('CEAF_e P/R/F', ceaf_e(a_referents, b_referents))
print('MUC P/R/F', muc(a_refs, b_refs))
print('B3 P/R/f', b_cub(a_refs, b_refs))
print('CoNLL 0/0/F', conll(a_refs, b_refs))

#for _a, _b in sorted(alignments_m.items(), key=lambda x:a['mentions'][x[0]][0]):
#    print(sorted(a['mentions'][_a]), sorted(b['mentions'][_b]), sep='\t')
