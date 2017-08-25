# encoding=utf8
import sys
reload(sys)
sys.setdefaultencoding('utf8')
import networkx as nx
from DataManager import DBcall


def id_author(papers):
    # flds = ["first_name", "last_name", "af_place", "initials"]
    flds = ["first_name", "last_name", "initials", "af_place", "af_country"]    
    pubs_to_author = {}
    a_pubs = {}
    for pubmed, authors in papers.iteritems():
        for d in authors:
            name = string_name(d, flds)
            if name != "":
                try:
                    pubs_to_author[name]
                except:
                    a_pubs = pubs_to_author(d, pubmed, papers, name, flds)
                    for k, v in a_pubs.iteritems():
                        if len(v) > 0:
                            print k, sorted(v, key=int)
                            pubs_to_author[k] = sorted(v, key=int)
    # merge author by longest metadata if they are met with the same name in the same paper:
    # metadata also can be written differently being visually the same, but in different encoding
    print "== cleaned =="
    ndata = dict(pubs_to_author)
    for nm, pbs in pubs_to_author.iteritems():
        for p in pbs:
            for c_nm, c_pbs in pubs_to_author.iteritems():
                if p in c_pbs and nm != c_nm:
                    if len(nm) >= len(c_nm):
                        try:
                            del ndata[c_nm]
                        except:
                            continue
                    else:
                        try:
                            del ndata[nm]
                        except:
                            continue
    for nm, pbs in ndata.iteritems():
        print nm, pbs


def pubs_to_author(d, pubmed, papers, name, flds):
    pubs = []
    for pm, authors in papers.iteritems():
        if pm != pubmed:
            for dd in authors:
                def_id = 0
                for f in flds:
                    try:
                        if d[f] != dd[f]:
                            def_id += 1
                    except:
                        continue
                if def_id == 0 and string_name(dd, flds) != "":
                    pubs.append(pm)
    # more than a given pubmed
    if len(pubs) > 0:
        pubs.append(pubmed)
    return {str(name): pubs}


def string_name(d, flds):
    uname = []
    found = []
    for f in flds:
        try:
            uname.append(d[f])
            found.append(f)
        except:
            continue
    if len(found) > 1:
        try:
            return ";".join(uname)
        except:
            return ""
    else:
        return ""


def main():
    G = nx.Graph()
    keys = {"pubmed": {'$gt': 0}}
    # papers = DBcall("papers", 0).findDatalistSorted(keys, "pubmed", 1).limit(1000)
    papers = DBcall("papers", 0).findDatalist(keys).limit(1000)
    sp = {}
    pps = []
    for p in papers:
        pps.append(p["pubmed"])
        sp[ p["pubmed"] ] = p["authors"]

    G.add_nodes_from(pps)
    id_author(sp)

# def make_edge(papers):
#     for p in papers:

if __name__ == '__main__':
    main()
