import os
import xml.etree.ElementTree as etree
from DataManager import DBcall, putLog
from datetime import datetime
from os import listdir
from os.path import isfile, join
import gzip

xmLpath = "./PubMed/ftp.ncbi.nlm.nih.gov/pubmed/baseline/"
gzips = [f for f in listdir(xmLpath) if isfile(join(xmLpath, f)) and f[-3:] == ".gz"]

# get our big file by chunks to process it serially:
# name space for author & paper:
names_a = {"LastName": "last_name", "ForeName": "first_name", "Initials": "initials", "ORCID": "orcid", "Affiliation": "af_place", "Country": "af_country"}
names_p = {"ArticleTitle": "title", "AbstractText": "abstract", "ISSN": "issn", "Title": "journal"}
months = {"Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6, "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12}
print str(datetime.now())[:-7] + " : start unzip and updating all gzip files one by one"
nn = 0
for gz in sorted(gzips)[:110]:
    values = {}
    keys = {}
    xmL = xmLpath + gz
    with gzip.open(xmL, 'rb') as f:
        xmL = xmL[:-3]
        with open(xmL, "w") as ff:
            try:
                ff.write(f.read())
            except Exception, e:
                print "failed to unpack " + gz + "exception: " + e
                continue
    values["xml_source"] = gz
    print str(datetime.now())[:-7] + " : starting to update data from " + xmL
    for event, elem in etree.iterparse(xmL, events=('start', 'end', 'start-ns', 'end-ns')):
        childs = {"Year": "1000", "Month": "1", "Day": "1"}
        if event == 'start':
            for k, v in elem.attrib.iteritems():
                if k == "IdType" and v == "pubmed":
                    keys["paper.pubmed"] = elem.text
        if elem.tag == 'PubmedArticle' and event == 'end':
            DBcall("papers", nn).updateData(keys, values)
    nn += 1
    print str(datetime.now())[:-7] + " : finished updating from " + str(nn) + "th " + xmL
    os.unlink(xmL)
print str(datetime.now())[:-7] + " : done"
