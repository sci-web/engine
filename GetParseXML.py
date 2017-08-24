# encoding=utf8
import sys
reload(sys)
sys.setdefaultencoding('utf8')
import re
import os
import xml.etree.ElementTree as etree
from DataManager import DBcall, putLog
from datetime import datetime
from os import listdir
from os.path import isfile, join
import gzip
import shutil

xmLpath = "./PubMed/ftp.ncbi.nlm.nih.gov/pubmed/baseline/"
gzips = [f for f in listdir(xmLpath) if isfile(join(xmLpath, f)) and f[-3:] == ".gz"]

# get our big file by chunks to process it serially:
# name space for author & paper:
names_a = {"LastName": "last_name", "ForeName": "first_name", "Initials": "initials", "ORCID": "orcid", "Affiliation": "af_place", "Country": "af_country"}
names_p = {"ArticleTitle": "title", "AbstractText": "abstract", "ISSN": "issn", "Title": "journal"}
months = {"Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6, "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12}
print "start unzip and loading all gzip files one by one: " + str(datetime.now())
k = 0
for gz in sorted(gzips):
    xmL = xmLpath + gz
    with gzip.open(xmL, 'rb') as f:
        xmL = xmL[:-3]
        with open(xmL, "w") as ff:
            ff.write(f.read())
    data = {}
    names = []
    pdate = []
    a_data = {}
    af_data = {}
    p_data = {}
    ca_data = {}
    ca_list = []
    kw_list = []
    n = 0   # line number to catch parcing/loading bugs
    print "start loading " + xmL + " : " + str(datetime.now())
    for event, elem in etree.iterparse(xmL, events=('start', 'end', 'start-ns', 'end-ns')):
        childs = {"Year": "1000", "Month": "1", "Day": "1"}
        memo = {}
        if event == 'start':
            date = ""
            for child in elem:
                if child.text:
                    childs[child.tag] = child.text
                if len(childs) == 0:
                    if hasattr(elem, 'getroot'):
                        elem = elem.getroot()
            for k, v in names_a.iteritems():
                if k == elem.tag:
                    a_data[v] = elem.text
                    if k == "Affiliation" and elem.text is not None:
                        words = elem.text.split(" ")
                        for w in words:
                            if re.search(r'\w+\@\w+\.\w+', w):
                                if re.search(r'\.$', w):
                                    w = w[:-1]
                                a_data["email"] = w

            for k, v in names_p.iteritems():
                if k == elem.tag:
                    p_data[v] = elem.text
            if elem.tag == "PubDate":
                month = childs["Month"]
                if not re.match("\d", month):
                    month = months[childs["Month"]]
                date = datetime.strptime(childs["Year"] + "-" + str(month) + "-" + childs["Day"], "%Y-%m-%d")
                p_data["pub_date"] = date

            for k, v in elem.attrib.iteritems():
                if k == "PubStatus":
                    date = datetime.strptime(childs["Year"] + "-" + childs["Month"] + "-" + childs["Day"], "%Y-%m-%d")
                if k == "PubStatus" and v == "received":
                    p_data["received_date"] = date
                if k == "PubStatus" and v == "accepted":
                    p_data["accepted_date"] = date
                if k == "IdType" and v == "pubmed":
                    p_data["pubmed"] = elem.text
                if k == "IdType" and v == "doi":
                    p_data["doi"] = elem.text
                if k == "Source" and v == "ORCID":
                    if re.search('http://orcid.org', elem.text):
                        a_data["orcid"] = elem.text
                    elif re.search('-', elem.text) and not re.search('http://orcid.org', elem.text):
                        a_data["orcid"] = 'http://orcid.org/' + elem.text
                    else:
                        a_data["orcid"] = 'http://orcid.org/' + elem.text[0:4] + "-" + elem.text[4:8] + "-" + elem.text[8:12] + "-" + elem.text[12:16]
                p_data["num_of_authors"] = len(ca_list)
                data["paper"] = p_data
            if elem.tag == "Keyword":
                kw_list.append(elem.text)
                # print event, elem.tag, elem.attrib, '>', elem.text, '<', date  #, json
        if elem.tag == 'Author' and event == 'end':
            a_data["position"] = len(ca_list) + 1
            ca_list.append(a_data)
            a_data = {}
        if elem.tag == 'PubmedArticle' and event == 'end':
            if len(ca_list) > 0:
                data["author"] = ca_list[0]
            ca_list = ca_list[1:]
            data["coauthors"] = ca_list
            data["keywords"] = kw_list
            DBcall("papers", n).loadData([data])
            # for k, v in data.iteritems():
            #     print k, v
            af_data = {}
            p_data = {}
            data = {}
            ca_list = []
            kw_list = []
        n += 1
    k += 1
    print "end loading " + k + "th " + xmL + " : " + str(datetime.now())
    with open(xmL, 'rb') as f_in, gzip.open(xmL + '.gz', 'wb') as f_out:
        shutil.copyfileobj(f_in, f_out)
    os.unlink(xmL)
