import sys
import json
import xml.etree.ElementTree as ET
import re
from collections import defaultdict
#from nltk.tokenize import TweetTokenizer
from nltk.tokenize import TreebankWordTokenizer
import nltk.data

'''
python %s xml source outfile_prefix end_char_excl    # (1519)
'''




def passage_splits(filename, end_offsets):
    i = 1
    char_counter = 0
    SPLIT_NAME = 'red_xml2ucoref.splt.tmp'
    split = open(SPLIT_NAME, 'w')
    with open(filename) as f:
        for line in f:
            for char in line:
                split.write(char)
                if str(char_counter) in end_offsets:
                    split.write('\n')
                    split.close()
                    yield (i, SPLIT_NAME)
                    split = open(SPLIT_NAME, 'w')
                char_counter += 1
    split.close()



filename_coref = sys.argv[1]
filename_source = sys.argv[2]
outfile_prefix = sys.argv[3]
end_offsets = sys.argv[4].split()


doc_id = filename_source.split('/')[-1]

tree = ET.parse(filename_coref)
root = tree.getroot()

'''
get mention and coref info
'''

span2a = defaultdict(dict)
id2m = {}
m2ref = {}
referents = {}

anno = root.find('annotations')

for entity in anno.findall('entity'):
    start, end = entity.find('span').text.split(',')
    ID = entity.find('id').text
    tag = entity.find('type').text
    id2m[ID] = entity
    span2a[int(start)] = {'id': ID, 'start': int(start), 'end': int(end), 'tag': tag}

for relation in anno.findall('relation'):
    ID = relation.find('id').text
    tag = relation.find('type').text
    props = relation.find('properties')
    ref = []
    if tag == 'IDENTICAL':
        ref.append(props.find('FirstInstance').text)
        for coref in props.findall('Coreferring_String'):
            ref.append(coref.text)

        for m in ref:
            m2ref[m] = ID

        referents[ID] = ref

for relation in anno.findall('relation'):
    ID = relation.find('id').text
    tag = relation.find('type').text
    props = relation.find('properties')
    if tag in ('APPOSITIVE',):
        ref = []
        for op in ('Head', 'Attribute'):
            m = props.find(op).text
            if m in m2ref:
                old_ref = m2ref[m]
                ref.extend(referents[old_ref])
                m2ref[m] = ID
                referents.pop(old_ref)
            else:
                ref.append(m)

#for relation in anno.findall('relation'):
#    ID = relation.find('id').text
#    tag = relation.find('type').text
#    props = relation.find('properties')
#    if tag in ('BRIDGING',):
#        ref = []
#        arg1, arg2 = anno.find(props.find('Argument').text, anno.find(props.find('Related_to').text
#        if id2m[arg1].find('Polarity') == id2m[arg2].find('Polarity'):
#        for op in ('Argument', 'Related_to'):
#            m = props.find(op).text
#            if m in m2ref:
#                old_ref = m2ref[m]
#                ref.extend(referents[old_ref])
#                m2ref[m] = ID
#                referents.pop(old_ref)
#            else:
#                ref.append(m)




tknzr = TreebankWordTokenizer()


for i, split in passage_splits(filename_source, end_offsets):

    '''
    get tokens
    '''

    tokens = []
    mentions = {}
    m2a = {}
    with open(split) as f:
        char_offs = 0
        acc = ''
        span = {'end': 0}
        in_xml_tag = False
        for line in f:
            for char in line:
                if char == '<':
                    in_xml_tag = True
                if in_xml_tag:
                    if char == '>':
                        in_xml_tag = False
                else:
                    if acc and char_offs == span['end']:
                        token_offs = len(tokens)
                        toks = tknzr.tokenize(acc)
                        m_toks = []
                        for j, tok in enumerate(toks, start=token_offs):
                            m_toks.append(j)
                            tokens.append(tok)
                        mentions[span['id']] = m_toks
                        m2a[span['id']] = span
                        acc = ''
                    if char_offs in span2a:
                        if acc:  # we have collected non-mention chars
                            token_offs = len(tokens)
                            toks = tknzr.tokenize(acc)
                            for tok in toks:
                                tokens.append(tok)
                        span = span2a[char_offs]
                        acc = ''
                    acc += char
                char_offs += 1

    local_referents = {}
    for k, v in referents.items():
        _v = [m for m in v if m in mentions]
        if _v:
            local_referents[k] = _v
    j = 1
    for m in mentions:
        if m not in m2ref:
            local_referents[f'singleton_{j}@r@{doc_id}@gold'] = [m]
            j += 1

    sent_detector = nltk.data.load('tokenizers/punkt/english.pickle')
    sentences = sent_detector.sentences_from_tokens(tokens)

    with open(f'{outfile_prefix}_{i}.tok.txt', 'w') as f:
        for sent in sentences:
            print(' '.join(sent), file=f)

    with open(f'{outfile_prefix}_{i}.ucoref.json', 'w') as f:
        d = {}
        d['tokens'] = tokens
        d['m2a'] = m2a
        d['mentions'] = mentions
        d['referents'] = local_referents
        json.dump(d, f, indent=2)

