import sys
import json

from collections import Counter

file1 = sys.argv[1]
file2 = sys.argv[2]

'''
python %s file1.ucoref.json file2.ucoref.json"
'''

def f1(a, b):
    return 0 if a+b == 0 else (2*a*b)/(a+b)

_score = lambda a, b: f1(a,b)
mu = 0.0
eta = 0.1


mu = int((mu * 10) - 1)
eta = int(eta * -10)

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
partial_m_a = 0
partial_m_b = 0
alignments_m = {}
alignments_m_by_a_tag = Counter()
alignments_m_by_b_tag = Counter()

for mention_b, tokens_b in b['mentions'].items():
    if not tokens_b:
        imp_b += 1

# greedy mention alignment
for _theta_m in range(10, mu, int(eta)):
    theta_m = _theta_m * 0.1
    for mention_a, tokens_a in a['mentions'].items():
        if not tokens_a:
            imp_a += 1
            continue

        if mention_a in alignments_m.keys(): continue

        aligned = None
        max_score = 0
        max_overlap = 0
        for mention_b, tokens_b in b['mentions'].items():
            if not tokens_b or mention_b in alignments_m.values(): continue
            overlap = len([t for t in tokens_a if t in tokens_b])
            score = _score((overlap/len(tokens_a)), (overlap/len(tokens_b)))
            if score > max_score:
                aligned = (mention_b, tokens_b)
                max_score = score
                max_overlap = overlap

        if max_score > theta_m and aligned:
            alignments_m[mention_a] = aligned[0]
            alignments_m_by_a_tag[a['m2a'][mention_a]['tag']] += 1
            alignments_m_by_b_tag[b['m2a'][aligned[0]]['tag']] += 1
            partial_m_a += max_overlap/len(tokens_a)
            partial_m_b += max_overlap/len(aligned[1])
            if max_score == 1.0:
                exact_m += 1

print('MENTIONS\n')
for m_a, m_b in alignments_m.items():
    print(' '.join([a['tokens'][i] for i in sorted(a['mentions'][m_a])]))
    print(' '.join([b['tokens'][i] for i in sorted(b['mentions'][m_b])]))
    print()


exact_r = 0
partial_r_a = 0
partial_r_b = 0
alignments_r = {}
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

b_referents = {}
for referent_b, mentions_b in b['referents'].items():
    b_referents[referent_b] = [str(m) for m in mentions_b]

# greedy referent alignment
for _theta_r in range(10, mu, int(eta)):
    theta_r = _theta_r * 0.1
    for referent_a, mentions_a in a['referents'].items():
        mentions_a = [str(m) for m in mentions_a]

        if referent_a in alignments_r.keys(): continue
        
        aligned = None
        max_score = 0
        max_overlap = 0
        for referent_b, mentions_b in b_referents.items():
            if referent_b in alignments_r.values(): continue
            overlap = len([m for m in mentions_a if alignments_m.get(m) in mentions_b])
            score = _score((overlap/len(mentions_a)), (overlap/len(mentions_b)))
            if score > max_score:
                aligned = (referent_b, mentions_b)
                max_score = score
                max_overlap = overlap

        if max_score > theta_r:
            alignments_r[referent_a] = aligned[0]
            a_type = 'Entity'
            b_type = 'Entity'
            for ref_type in equiv.values():
                if any(equiv.get(a.get('m2a', {}).get(m)['tag']) == ref_type for m in mentions_a):
                    a_type = ref_type
                if any(equiv.get(b.get('m2a', {}).get(m)['tag']) == ref_type for m in aligned[1]):
                    b_type = ref_type
            alignments_r_by_a_type[a_type] += 1
            alignments_r_by_b_type[b_type] += 1
            partial_r_a += max_overlap/len(mentions_a)
            partial_r_b += max_overlap/len(aligned[1])
            if max_score == 1.0:
                exact_r += 1

print('\nREFERENTS\n')
for r_a, r_b in alignments_r.items():
    print(', '.join(['_'.join([a['tokens'][i] for i in sorted(a['mentions'][str(m_a)])]) for m_a in a['referents'][r_a]]))
    print(', '.join(['_'.join([b['tokens'][i] for i in sorted(b['mentions'][str(m_b)])]) for m_b in b['referents'][r_b]]))
    print()


def f1(tp, a, b):
    p = tp/a
    r = tp/b
    return (2*p*r)/(p+r)

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
a_r = len(a['referents'])
b_r = len(b['referents'])

print('''\\hline
\\textbf{referents}  \\\\
\\hline''')
#print('\nreferents')
print('exact', ex_r, '-', '-', sep=' & ', end=' \\\\\n')
print('fuzzy', al_r, f'{ex_r*100/al_r:.1f}', '-', sep=' & ', end=' \\\\\\hline\n')
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


#for _a, _b in sorted(alignments_m.items(), key=lambda x:a['mentions'][x[0]][0]):
#    print(sorted(a['mentions'][_a]), sorted(b['mentions'][_b]), sep='\t')
