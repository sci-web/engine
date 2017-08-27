# encoding=utf8
import sys
import networkx as nx
import random
from DataManager import DBcall
from datetime import datetime
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
                    a_pubs = authorPubs(d, pubmed, papers, name, flds)
                    for k, v in a_pubs.iteritems():
                        if len(v) > 0:
                            # print k, sorted(v, key=int)
                            pubs_to_author[k] = sorted(v, key=int)
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
                # def_id = 0 if the same author, including with undef fields:
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


def AuthorsToPubs(adata, flds):
    a_to_pubs = {}
    print len(adata.keys())
    # put author data in the DB with assigned id and list of papers
    authors_w_p = {}
    for num in range(len(adata.keys())):
        au = adata.keys()[num]
        adata_nums = {}
        adata_nums["assigned_id"] = num + 1
        meta = {}
        for f in range(len(flds)):
            meta[flds[f]] = adata.keys()[num].split(";")[f]
        adata_nums["meta"] = meta
        adata_nums["papers"] = adata[au]
        authors_w_p[num + 1] = adata[au]
        # print num, adata.keys()[num], adata[ adata.keys()[num] ]
        # to link all co-authors with assigned id in the paper:
        for p in adata[au]:
            try:
                a_to_pubs[p].append(adata_nums["assigned_id"])
            except:
                a_to_pubs[p] = [adata_nums["assigned_id"]]

        DBcall("authors", num).loadData([adata_nums])
        print num + 1, adata[au]
    return a_to_pubs, authors_w_p


def MakeGraphData(a_to_pubs):
    keys = {"assigned_id": {'$gt': 0}}
    authors = DBcall("authors", 0).findDatalist(keys)
    e_tuples = {}
    for au in authors:
        # print nm, pbs
        for p in au["papers"]:
            all_a = a_to_pubs[p]
            for a in all_a:
                if a != au["assigned_id"]:
                    try:
                        e_tuples[a, au["assigned_id"]] += 1
                    except:
                        e_tuples[a, au["assigned_id"]] = 1
    return e_tuples


def main():
    flds = ["first_name", "last_name", "initials", "af_place", "af_country"]
    print str(datetime.now())[:-7] + " : extract data"
    keys = {"pubmed": {'$gt': 0}}
    # or findDatalistSorted(keys, "pubmed", 1).limit(1000)
    papers = DBcall("papers", 0).findDatalist(keys).limit(10)
    sp = {}
    pps = []
    for p in papers:
        pps.append(p["pubmed"])
        if len(p["authors"]) > 0:
            sp[p["pubmed"]] = p["authors"]
    # authors with their papers (more than 1 paper):
    print str(datetime.now())[:-7] + " : start data linking"
    pubs_to_author = idAuthor(sp, flds)
    """
    we might have got here a list of authors where some has different fields,
    but the same firs_name, last_name, initials:
    merge authors by longest metadata if they are met under the same name
    (first, last name, initials) in the same paper list (name + affiliation):
    the same metadata also can be RW differently being in different encoding
    """
    edges = []
    adata = dict(pubs_to_author)
    print len(pubs_to_author.keys())
    for nm, pbs in pubs_to_author.iteritems():
        for p in pbs:
            for c_nm, c_pbs in pubs_to_author.iteritems():
                # if in the same p in a list of pprs assigned to another author...
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

    print list(set(pubs_to_author.keys()) - set(adata.keys()))

    e_tuples = MakeGraphData(a_to_pubs)

    aus = len(authors_w_p.keys())
    print str(datetime.now())[:-7] + " : " + str(aus) + " authors"
    print str(datetime.now())[:-7] + " : end linking"

    count_n = len(e_tuples.keys())
    G = nx.Graph()
    seed = [(x, y) for x in range(count_n) for y in range(1, count_n)]
    nodes = {}
    for node, weight in e_tuples.iteritems():
        n1, n2 = node
        for nn in node:
            try:
                nodes[nn]
            except:
                G.add_node(nn)
                [G.node[nn]['pos']] = random.sample(seed, 1)
                nodes[nn] = 1
        G.add_edge(n1, n2, weight=e_tuples[node])
    pos = nx.get_node_attributes(G, 'pos')

    dmin = 1
    ncenter = 0
    for n in pos:
        x, y = pos[n]
        d = (x-0.5)**2+(y-0.5)**2
        if d < dmin:
            ncenter = n
            dmin = d
    # p = nx.single_source_shortest_path_length(G, ncenter)
    print G.nodes()
    # print G.edges()

    edge_trace = Scatter(
        x=[],
        y=[],
        line=Line(width=0.5, color='#888'),
        hoverinfo='none',
        mode='lines')

    for edge in G.edges():
        # print edge
        x0, y0 = G.node[edge[0]]['pos']
        x1, y1 = G.node[edge[1]]['pos']
        edge_trace['x'] += [x0, x1, None]
        edge_trace['y'] += [y0, y1, None]

    node_trace = Scatter(
        x=[],
        y=[],
        text=[],
        mode='markers',
        hoverinfo='text',
        marker=Marker(
            showscale=True,
            # colorscale other options
            # 'Greys' | 'Greens' | 'Bluered' | 'Hot' | 'Picnic' | 'Portland' |
            # Jet' | 'RdBu' | 'Blackbody' | 'Earth' | 'Electric' | 'YIOrRd'
            colorscale='YIGnBu',
            reversescale=True,
            color=[],
            size=10,
            colorbar=dict(
                thickness=15,
                title='Node Connections',
                xanchor='left',
                titleside='right'
            ),
            line=dict(width=2)))

    for node in G.nodes():
        x, y = G.node[node]['pos']
        node_trace['x'].append(x)
        node_trace['y'].append(y)
    print "Xs:" + str(len(node_trace['x'])) + " coord: " + str(node_trace['x'][4])
    print "Ys:" + str(len(node_trace['y'])) + " coord: " + str(node_trace['y'][4])
    # for gn in G.nodes():
    #     print gn, G.neighbors(gn)
    # >>> G.add_path([0,1,2,3])
    # >>> [(n,nbrdict) for n,nbrdict in G.adjacency_iter()]
    # [(0, {1: {}}), (1, {0: {}, 2: {}}), (2, {1: {}, 3: {}}), (3, {2: {}})]
    # print enumerate(G.adjacency_list())
    for node, adjacencies in G.adjacency_iter():
        node_trace['marker']['color'].append(len(adjacencies))
        node_info = str(node) + ' # of connections: '+str(len(adjacencies))
        node_trace['text'].append(node_info)
    fig = Figure(data=Data([edge_trace, node_trace]),
                 layout=Layout(
                     title='<br>Network graph made with Python',
                     titlefont=dict(size=16),
                     showlegend=False,
                     hovermode='closest',
                     margin=dict(b=20, l=5, r=5, t=40),
                     annotations=[dict(
                         text="Thanks to PlotLy",
                         showarrow=False,
                         xref="paper", yref="paper",
                         x=0.005, y=-0.002)],
                     xaxis=XAxis(showgrid=False, zeroline=False, showticklabels=False),
                     yaxis=YAxis(showgrid=False, zeroline=False, showticklabels=False)))
    plotly.offline.plot(fig, filename='networkx')
# def makeEdges(papers):
#     for p in papers:

if __name__ == '__main__':
    main()
