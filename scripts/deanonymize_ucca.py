import sys
from ucca import convert as uconv, layer0 as ul0


filename = sys.argv[1]
reference = sys.argv[2]
retain_newlines = 'newlines' in sys.argv


name = filename.rsplit('.', 1)[0]

tokens = []
with open(reference) as f:
    for i, line in enumerate(f):
        if retain_newlines and i>0:
            tokens.append('\n')
        if line:
            for t in line.split():
                tokens.append(t)

p = uconv.file2passage(filename)

assert len(p.layer(ul0.LAYER_ID).pairs) == len(tokens)

for (_, tok), txt in zip(p.layer(ul0.LAYER_ID).pairs, tokens):
    tok._attrib['text'] = txt


uconv.passage2file(p, f'{name}.deano.xml')
