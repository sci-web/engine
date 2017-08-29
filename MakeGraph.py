# encoding=utf8
import sys
import networkx as nx
import random
from DataManager import DBcall
from datetime import datetime
import operator
import math
# import plotly.plotly as py
import plotly
from plotly.offline import download_plotlyjs, init_notebook_mode, plot, iplot
from plotly.graph_objs import *
# from plotly.graph_objs import Scatter, Figure, Layout

reload(sys)
sys.setdefaultencoding('utf8')


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
                    # author papers with author positions
                    a_pubs = authorPubs(d, pubmed, papers, name, flds, d["position"], len(authors))
                    for k, v in a_pubs.iteritems():
                        if len(v) > 0:
                            # print k, sorted(v, key=int)
                            pubs_to_author[k] = sorted(v)
    return pubs_to_author


def authorPubs(d, pubmed, papers, name, flds, pos, coauthors):
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
                # def_id = 0 if the same author, including with undef fields:
                if def_id == 0 and stringName(dd, flds) != "":
                    pubs.append([pm, dd["position"], len(authors)])
    # if len(pubs) > 0:   # remove this condition if authors with < 2 papers
    pubs.append([pubmed, pos, coauthors])
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
        print(d)
        return ""


def AuthorsToPubs(adata, flds):
    a_to_pubs = {}
    print(len(adata.keys()))
    # put author data in the DB with assigned id and list of papers
    authors_w_p = {}
    for num in range(len(adata.keys())):
        au = adata.keys()[num]
        adata_nums = {}
        #  starting from 1 billion
        a_id = 1000000000 + num + 1
        adata_nums["assigned_id"] = a_id
        for f in range(len(flds)):
            adata_nums[flds[f]] = adata.keys()[num].split(";")[f]
        p_list = []
        for pps in adata[au]:
            pubmed = pps[0]
            position = pps[1]
            coauthors = pps[2]
            p_list.append({"pubmed": pubmed, "position": position, "coauthors": coauthors})
            try:
                a_to_pubs[pubmed].append(adata_nums["assigned_id"])
            except:
                a_to_pubs[pubmed] = [adata_nums["assigned_id"]]
        adata_nums["papers"] = p_list
        authors_w_p[a_id] = adata[au]
        # print num, adata.keys()[num], adata[ adata.keys()[num] ]
        # to link all co-authors with assigned id in the paper:

        DBcall("authors", num).loadData([adata_nums])
        # print num + 1, adata[au]
    return a_to_pubs, authors_w_p


def MakeGraphData(a_to_pubs):
    keys = {"assigned_id": {'$gt': 0}}
    authors = DBcall("authors", 0).findDatalist(keys)
    e_tuples = {}
    for au in authors:
        # print nm, pbs
        for p in au["papers"]:
            all_a = a_to_pubs[p["pubmed"]]
            for a in all_a:
                if a != au["assigned_id"]:
                    try:
                        e_tuples[a, au["assigned_id"]] += 1
                    except:
                        e_tuples[a, au["assigned_id"]] = 1
    return e_tuples


def main():
    flds = ["first_name", "last_name", "initials", "af_place", "af_country", "orcid", "email"]
    print(str(datetime.now())[:-7] + " : extract data")
    keys = {"pubmed": {'$gt': 0}}
    # or findDatalistSorted(keys, "pubmed", 1).limit(1000)
    papers = DBcall("papers", 0).findDatalist(keys).limit(10000)
    authors_to_pubmed = {}
    pps = []
    for p in papers:
        pps.append(p["pubmed"])
        if len(p["authors"]) > 0:
            authors_to_pubmed[p["pubmed"]] = p["authors"]
            # positions = []
            # for p_a in p["authors"]:
            #     positions.append(p_a["positions"])
    # authors with their papers (more than 1 paper):
    print(str(datetime.now())[:-7] + " : start data linking")
    pubs_to_author = idAuthor(authors_to_pubmed, flds)
    """
    we might have got here a list of authors where some has different fields,
    but the same firs_name, last_name, initials:
    so let's merge authors by longest metadata if they are met under the same
    name (first, last, initials) in the same paper list (name+affiliation):
    the same metadata also can be RW differently being in different encoding
    """
    edges = []
    adata = dict(pubs_to_author)
    print(len(pubs_to_author.keys()))
    for nm, pbs in pubs_to_author.iteritems():
        for p in pbs:
            for c_nm, c_pbs in pubs_to_author.iteritems():
                # if the same p in this list of pprs assigned to
                # another author...
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

    a_to_pubs, authors_w_p = AuthorsToPubs(adata, flds)

    print(list(set(pubs_to_author.keys()) - set(adata.keys())))

    e_tuples = MakeGraphData(a_to_pubs)
    count_n = len(e_tuples.keys())
    aus = len(authors_w_p.keys())
    print(str(datetime.now())[:-7] + " : " + str(aus) + " authors")
    print(str(datetime.now())[:-7] + " : end linking")

    G = nx.Graph()
    nodes = {}
    for node, weight in e_tuples.iteritems():
        n1, n2 = node
        for nn in node:
            try:
                nodes[nn]
            except:
                G.add_node(nn)
                nodes[nn] = 1
        G.add_edge(n1, n2, weight=e_tuples[node])


if __name__ == '__main__':
    main()
