import sys
import json
from collections import defaultdict

'''
python %s GUM_whow_parachute ./GUM_whow_parachute "23-19 36-39"
## python %s GUM_whow_parachute ./GUM_whow_parachute "1-1_23-19 24-1_36-39"
'''

filename_gum = sys.argv[1]
outfile_prefix = sys.argv[2]
end_offsets = sys.argv[3].split()


gum_tokens = []
gum_token_ids = []
acc = []
id_acc = []
with open(filename_gum) as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith('#'):
            fields = line.split()
            ID, _, word, ent_type, inf_status, coref_type, link = fields
            acc.append(fields)
            id_acc.append(ID)
            
            if ID in end_offsets:
                if acc:
                    gum_tokens.append(acc)
                    gum_token_ids.append(id_acc)
                acc = []
                id_acc = []

carryover_links = set()
ind_offset = 1
for i, (gum_tok, gum_tok_ids) in enumerate(zip(gum_tokens, gum_token_ids), start=1):

    gum_tok2m = defaultdict(dict)
    gum_m2a = {}
    gum_mentions = {}
    gum_m2ref = {}
    gum_referents = {}
    
    for gt in gum_tok:
        
        ID, _, _, ref_type, inf_status, coref_type, links = gt
        
        if inf_status != '_':
            _status = inf_status.split('|')
            for stat_ind in _status:
                _stat_ind = stat_ind.strip(']').split('[')
                if len(_stat_ind) == 2:
                    ind = int(_stat_ind[1])
                    gum_tok2m[ID][ind] = ind
                else:
                    ind = ind_offset + 1
                    gum_tok2m[ID][0] = ind

                ind_offset = max(ind_offset, ind)
                    
                if ind not in gum_mentions:
                    gum_mentions[ind] = []
                    gum_m2a[ind] = {'tag': ref_type.strip(']').split('[')[0]}
                if gum_tok_ids.index(ID) not in gum_mentions[ind]:
                    gum_mentions[ind].append(gum_tok_ids.index(ID))

                status = _stat_ind[0]

                if (status in ('new', 'acc') or ID in carryover_links):
                    gum_referents[ind] = [ind]
                    gum_m2ref[ind] = ind


    not_resolved = set() # for cataphors

    for gt in gum_tok:

        ID = gt[0]
        coref_type = gt[5]
        links = gt[6]
        
        if links != '_':
            for link, typ in zip(links.split('|'), coref_type.split('|')):
                _link_ind = link.strip(']').split('[')
                if len(_link_ind) == 2:
                    lID, _ind = _link_ind # '18-10', '70_66'
                else:
                    lID, _ind = link, '0_0'
                _l_ind, _m_ind = _ind.split('_') # '70', '66'
                if _m_ind == '0':
                    m_ind = gum_tok2m[ID][0]
                else:
                    m_ind = int(_m_ind) # 66

                try:
                    if lID  not in gum_tok2m:
                        raise KeyError(lID)
                    if _l_ind == '0':
                        l_ind = gum_tok2m[lID][0]
                    else:
                        l_ind = int(_l_ind)
                except KeyError as e:
                    # link pointing outside of passage
                    carryover_links.add(lID)
                else:
                    if typ == 'bridge':
                        gum_referents[l_ind] = [l_ind]
                        gum_m2ref[l_ind] = l_ind
                    elif typ == 'cata':
                        assert l_ind in gum_m2ref
                        if m_ind in gum_m2ref: # merge clusters of cataphor and antecendent
                            for m in gum_referents[gum_m2ref[m_ind]]:
                                if m not in gum_referents[gum_m2ref[l_ind]]:
                                    gum_referents[gum_m2ref[l_ind]].append(m)
                            gum_referents.pop(gum_m2ref[m_ind])
                            gum_m2ref[m_ind] = gum_m2ref[l_ind]
                        resolved = set()
                        for unr in not_resolved: # targets of backward links that are unresolved due to cataphor
                            unr_ID, unr_m_ind, unr_lID, unr_l_ind = unr
                            if ID == unr_lID and m_ind == unr_l_ind:
                                gum_referents[gum_m2ref[l_ind]].append(unr_m_ind)
                                gum_m2ref[unr_m_ind] = gum_m2ref[l_ind]
                                resolved.add(unr)
                        not_resolved -= resolved
                    else:
                        if m_ind not in gum_m2ref: #, (gt, _m_ind, m_ind)
                            not_resolved.add((ID, m_ind, lID, l_ind))
                        else:
                            gum_m2ref[l_ind] = gum_m2ref[m_ind]
                            if l_ind not in gum_referents[gum_m2ref[m_ind]]:
                                # print('ok')
                                gum_referents[gum_m2ref[m_ind]].append(l_ind)

    assert len(not_resolved) == 0

    with open(f'{outfile_prefix}_{i}.ucoref.json', 'w') as f:
        d = {}
        d['tokens'] = [fields[2] for fields in gum_tok]
        d['m2a'] = gum_m2a
        d['mentions'] = gum_mentions
        d['referents'] = gum_referents
        json.dump(d, f, indent=2)
