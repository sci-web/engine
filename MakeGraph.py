# encoding=utf8
import sys
reload(sys)
sys.setdefaultencoding('utf8')
import networkx as nx
from DataManager import DBcall
from datetime import datetime
import matplotlib.pyplot as plt


def idAuthor(papers, flds):
    # flds = ["first_name", "last_name", "af_place", "initials"]
    pubs_to_author = {}
    a_pubs = {}
    for pubmed, authors in papers.iteritems():
        for d in authors:
            name = stringName(d, flds)
            if name != "":
                try:
                    pubs_to_author[name]
                except:
                    a_pubs = authorPubs(d, pubmed, papers, name, flds)
                    for k, v in a_pubs.iteritems():
                        if len(v) > 0:
                            # print k, sorted(v, key=int)
                            pubs_to_author[k] = sorted(v, key=int)
            else:
                print pubmed
    return pubs_to_author


def authorPubs(d, pubmed, papers, name, flds):
    pubs = []
    for pm, authors in papers.iteritems():
        # check out the author in all other than a given pubmed paper
        if pm != pubmed:
            for dd in authors:
                def_id = 0
                for f in flds:
                    # assign empty value to undefined fields:
                    try:
                        d[f]
                    except:
                        d[f] = ""
                    try:
                        dd[f]
                    except:
                        dd[f] = ""
                    # check if defined fields don't coincide
                    # (if not the same author in another paper)
                    if d[f] != dd[f] and dd[f] != "" and d[f] != "":
                        def_id += 1
                # def_id = 0 if the same author, including with undefined fields:
                if def_id == 0 and stringName(dd, flds) != "":
                    pubs.append(pm)
    # if len(pubs) > 0:   # remove this condition if authors with < 2 papers
    pubs.append(pubmed)
    return {str(name): pubs}


def stringName(d, flds):
    uname = []
    found = []
    for f in flds:
        try:
            if d[f] is not None:
                uname.append(d[f])
                found.append(f)
            else:
                uname.append("")
        except:
            uname.append("")
    # must be two fields at least to make a meaningfull record
    if len(found) > 1:
        return ";".join(uname)
    else:
        print d
        return ""


def main():
    G = nx.Graph()
    flds = ["first_name", "last_name", "initials", "af_place", "af_country"]    
    # papers = DBcall("papers", 0).findDatalistSorted(keys, "pubmed", 1).limit(1000)
    print str(datetime.now())[:-7] + " : extract data"
    keys = {"pubmed": {'$gt': 0}}
    papers = DBcall("papers", 0).findDatalist(keys).limit(100)
    sp = {}
    pps = []
    for p in papers:
        pps.append(p["pubmed"])
        if len(p["authors"]) > 0:
            sp[ p["pubmed"] ] = p["authors"]
    # authors with their papers (more than 1 paper):
    print str(datetime.now())[:-7] + " : start data linking"
    pubs_to_author = idAuthor(sp, flds)
    """
    we might have got here a list of authors where some has different fields,
    but the same firs_name, last_name, initials:
    merge authors by longest metadata if they are met under the same name
    (first, last name, initials) in the same paper list (i.e. name + affiliation):
    metadata also can be written differently being visually the same, but in different encoding
    """
    edges = []
    adata = dict(pubs_to_author)
    print len(pubs_to_author.keys())
    for nm, pbs in pubs_to_author.iteritems():
        for p in pbs:
            for c_nm, c_pbs in pubs_to_author.iteritems():
                # if in the same paper in a list of paper assigned to another author...
                if p in c_pbs and nm != c_nm:
                    # if metadata are different but name is the same:
                    nm_lst = nm.split(";")[:2]
                    c_nm_lst = c_nm.split(";")[:2]
                    if nm_lst == c_nm_lst:
                        if len(nm) >= len(c_nm):
                            try:
                                del adata[c_nm]
                            except:
                                continue
                        else:
                            try:
                                del adata[nm]
                            except:
                                continue                         
    a_to_pubs = {}
    print len(adata.keys())
    # put author data in the DB with assigned id and list of papers
    for num in range(len(adata.keys())):
        adata_nums = {}
        adata_nums["assigned_id"] = num + 1
        meta = {}
        for f in range(len(flds)):
            meta[flds[f]] = adata.keys()[num].split(";")[f]
        adata_nums["meta"] = meta
        adata_nums["papers"] = adata[ adata.keys()[num] ]
        # print num, adata.keys()[num], adata[ adata.keys()[num] ]
        # to link all co-authors with assigned id in the paper:
        for p in adata[ adata.keys()[num] ]:
            try:
                a_to_pubs[p].append(adata_nums["assigned_id"])
            except:
                a_to_pubs[p] = [adata_nums["assigned_id"]]

        DBcall("authors", num).loadData([adata_nums])

    print list(set(pubs_to_author.keys()) - set(adata.keys()))

    keys = {"assigned_id": {'$gt': 0}}
    authors = DBcall("authors", 0).findDatalist(keys)
    e_tuples = {}
    for au in authors:
        # print nm, pbs
        for p in au["papers"]:
            all_a = a_to_pubs[p]
            for a in all_a:
                if a != au:
                    try:
                        e_tuples[a, au["assigned_id"]] += 1
                    except:
                        e_tuples[a, au["assigned_id"]] = 1

    for node, weight in e_tuples.iteritems():
        n1, n2 = node
        G.add_nodes_from(node)
        G.add_edge(n1, n2, weight=e_tuples[node])
    print nx.connected_components(G)
    print nx.degree(G)
    nx.draw_shell(G)
    # pos = nx.spring_layout(G)
    # nx.draw_networkx_nodes(G, pos=pos, nodelist=G.nodes())
    # nx.draw_networkx_edges(G, pos=pos, edgelist=G.edges())
    plt.show()
    # print list(set(sp.keys()) - set(a_to_pubs.keys()))
    # for pp, au in a_to_pubs.iteritems():
    #     print pp, au
    print str(datetime.now())[:-7] + " : " + str(len(a_to_pubs.keys())) + " authors adding:"
    print str(datetime.now())[:-7] + " : end linking"
# def makeEdges(papers):
#     for p in papers:

if __name__ == '__main__':
    main()
