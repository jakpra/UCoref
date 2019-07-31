import sys
import json



filename = sys.argv[1]


with open(filename) as f:
    d = json.load(f)


tokens = d['tokens']
if isinstance(tokens, dict):
    tokens = tokens.values()
ntokens = 0
nsents = 0
for t in tokens:
    if t.strip():
        ntokens += 1
    else:
        nsents += 1
words = d.get('words', [])
units = d.get('units', [])
#ref2m = d['ref2m']
m2a = d['m2a']
#i2ref = d['i2ref']
#ref2i = {}
#for i, ref in enumerate(i2ref):
#    ref2i[ref] = i

mentions = d.get('mentions') or [k for k, v in m2a.items() if v['index'] != -1]
referents = d.get('referents') or d['i2ref']

_print = lambda *args, **kwargs: print(*args, sep='\t')

_print(nsents, 'total sentences')
_print(ntokens, 'total tokens')
_print(len(words), 'non-punctuation tokens')
_print(len(units), 'total units')
_print(len(m2a), 'candidate mentions')
_print(len(mentions), 'actual mentions')
_print(len(referents), 'referents')
