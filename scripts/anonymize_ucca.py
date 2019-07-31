import sys
from ucca import convert as uconv, layer0 as ul0



filename = sys.argv[1]

name = filename.rsplit('.', 1)[0]



p = uconv.file2passage(filename)



for i, t in p.layer(ul0.LAYER_ID).pairs:
    t._attrib['text'] = '<HIDDEN>'


uconv.passage2file(p, f'{name}.ano.xml')
