# encoding=utf8
import sys
import re
import os
import xml.etree.ElementTree as etree
from DataManager import DBcall, putLog
from datetime import datetime
from os import listdir
from os.path import isfile, join
import gzip
reload(sys)
sys.setdefaultencoding('utf8')
# import shutil


xmLpath = "./PubMed/ftp.ncbi.nlm.nih.gov/pubmed/baseline/"
gzips = [f for f in listdir(xmLpath) if isfile(join(xmLpath, f)) and f[-3:] == ".gz"]

# get our big file by chunks to process it serially:
# name space for author & paper:
names_a = {"LastName": "last_name", "ForeName": "first_name", "Initials": "initials", "ORCID": "orcid", "Affiliation": "af_place", "Country": "af_country"}
names_p = {"ArticleTitle": "title", "AbstractText": "abstract", "ISSN": "issn", "Title": "journal"}
months = {"Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6, "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12}
print str(datetime.now())[:-7] + " : start unzip and loading all gzip files one by one"
nn = 0
for gz in sorted(gzips)[80:]:
    xmL = xmLpath + gz
    with gzip.open(xmL, 'rb') as f:
        xmL = xmL[:-3]
        with open(xmL, "w") as ff:
            try:
                ff.write(f.read())
            except Exception, e:
                print "failed to unpack " + gz + "exception: " + e
                continue
    data = {}
    n = 0   # line number to catch parcing/loading bugs
    print str(datetime.now())[:-7] + " : starting to update " + xmL
    for event, elem in etree.iterparse(xmL, events=('start', 'end', 'start-ns', 'end-ns')):
        childs = {"Year": "1000", "Month": "1", "Day": "1"}
        # take fully populated event (i.e. event != start! )
        pubmed = 0
        if event == 'end':
            date = ""
            for child in elem:
                if child.text:
                    childs[child.tag] = child.text
                if len(childs) == 0:
                    if hasattr(elem, 'getroot'):
                        elem = elem.getroot()
            for k, v in names_p.iteritems():
                if k == elem.tag:
                    data[v] = elem.text
            for k, v in elem.attrib.iteritems():
                if k == "PubStatus":
                    try:
                        date = datetime.strptime(childs["Year"] + "-" + childs["Month"] + "-" + childs["Day"], "%Y-%m-%d")
                    except:
                        day = int(childs["Day"]) - 2
                        date = datetime.strptime(childs["Year"] + "-" + str(month) + "-" + str(day), "%Y-%m-%d")
                        putLog("Date format was wrong for pid (pid = records number), corrected for -2 days", n, "XML parcing" + gz, "format")
                    if v == "received":
                        data["received_date"] = date
                    if v == "accepted":
                        data["accepted_date"] = date
                if k == "IdType" and v == "pubmed" and elem.tag == "ArticleId":
                    data["pubmed"] = 0
                    if elem.text is not None:
                        pubmed = int(elem.text)
        if elem.tag == 'PubmedArticle' and event == 'end':
            keys = {"pubmed": pubmed}
            DBcall("papers", n).updateData(keys, data)
            data = {}
            pubmed = 0
            n += 1
    nn += 1
    print str(datetime.now())[:-7] + " : finished updateing " + str(nn) + "th " + xmL
    os.unlink(xmL)
print str(datetime.now())[:-7] + " : done"
