import sys
import json


filename = sys.argv[1]

name = filename.rsplit('.', 1)[0]


with open(filename) as f:
    d = json.load(f)


d.pop('tokens')


new_referents = {}
for i, (k, v) in enumerate(d['referents'].items()):
    new_referents[str(i)] = v

d['referents'] = new_referents


with open(f'{name}.ano.json', 'w') as f:
    json.dump(d, f, indent=2)
