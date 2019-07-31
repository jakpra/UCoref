import sys
import json


'''
python scripts/onto_jsonlines2ucoref.py annotations/onto/eng_0009_0.jsonlines  annotations/ucoref/onto/ 302
'''




def passage_splits(sentences, clusters, ner, end_offsets):
    _toks = []
    _ments = {}
    _m2a = {}
    _refs = {}
    toks2m = {}

    k = 0
    for sent in sentences:
        for tok in sent:
            _toks.append(tok)
            if str(k) in end_offsets:
                j = 1
                for i, cluster in enumerate(clusters, start=1):
                    ref = []
                    for mention in cluster:
                        first, last = mention
                        toks = list(range(first, last+1))
                        if max(toks) <= k:
                            _ments[j] = toks
                            toks2m[first, last] = j
                            _m2a[j] = {'ID': j, 'tag': 'SOME_TAG'}
                            ref.append(j)
                            j += 1
                    if len(ref) > 0:
                        _refs[i] = ref
                i = 1
                for ne in ner:
                    first, last, typ = ne
                    toks = list(range(first, last+1))
                    if max(toks) <= k:
                        if (first, last) not in toks2m:
                            _ments[j] = toks
                            _m2a[j] = {'ID': j, 'tag': typ}
                            _refs[f'NE_{i}'] = [j]
                            j += 1
                            i += 1
                        else:
                            _m2a[toks2m[first, last]]['tag'] = typ

                yield (_toks, _ments, _m2a, _refs)
            k += 1


filename_onto = sys.argv[1]
outfile_prefix = sys.argv[2]
end_offsets = sys.argv[3].split()
predicted = 'pred' in sys.argv

with open(filename_onto) as f:
    for line in f:
        d = json.loads(line)

        doc_id = d['doc_key'].rsplit('/', maxsplit=1)[-1]

        for i, (tokens, mentions, m2a, referents) in enumerate(passage_splits(d['sentences'], 
                d[('predicted_' if predicted else '') + 'clusters'], d['ner'], 
                end_offsets), start=1):


            with open(f'{outfile_prefix}_{doc_id}_{i}.ucoref.json', 'w') as f:
                d = {}
                d['tokens'] = tokens
                d['m2a'] = m2a
                d['mentions'] = mentions
                d['referents'] = referents
                json.dump(d, f, indent=2)
