import sys
import json


filename = sys.argv[1]
reference = sys.argv[2]

name = filename.rsplit('.', 1)[0]


with open(filename) as f:
    d = json.load(f)


tokens = []
with open(reference) as f:
    for line in f:
#        if retain_newlines and i>0:
#            tokens.append('\n')
        if line:
            for t in line.split():
                tokens.append(t)


#new_referents = {}
#for i, (k, v) in enumerate(d['referents'].items()):
#    new_referents[str(i)] = v

d['tokens'] = tokens #new_referents


with open(f'{name}.deano.json', 'w') as f:
    json.dump(d, f, indent=2)
