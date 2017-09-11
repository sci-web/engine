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


xmLpath = "./PubMed/ftp.ncbi.nlm.nih.gov/pubmed/updatefiles/"
gzips = [f for f in listdir(xmLpath) if isfile(join(xmLpath, f)) and f[-3:] == ".gz"]

# get our big file by chunks to process it serially:
# name space for author & paper:
names_a = {"LastName": "last_name", "ForeName": "first_name", "Initials": "initials", "ORCID": "orcid", "Affiliation": "af_place", "Country": "af_country"}
names_p = {"ArticleTitle": "title", "AbstractText": "abstract", "ISSN": "issn", "Title": "journal"}
months = {"Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6, "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12}
print str(datetime.now())[:-7] + " : start unzip and loading all gzip files one by one"
nn = 0
for gz in sorted(gzips)[160:]:
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
    ca_list = []
    kw_list = []
    a_data = {}
    n = 0   # line number to catch parcing/loading bugs
    updts = 0
    insrts = 0
    print str(datetime.now())[:-7] + " : starting to update with " + xmL
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

            if elem.tag == "PubDate" or elem.tag == "DateCreated":
                month = childs["Month"]
                if not re.match("\d", month):
                    month = months[childs["Month"]]
                try:
                    date = datetime.strptime(childs["Year"] + "-" + str(month) + "-" + childs["Day"], "%Y-%m-%d")
                except:
                    month = int(month)
                    day = int(childs["Day"])  # say, when 31 for Feb
                    if day > 28 and month == 2:
                        day = day - 3
                    if day > 30 and (month == 9 or month == 4 or month == 6 or month == 11):
                        day = day - 1
                    if day < 1:
                        day = 1
                    date = datetime.strptime(childs["Year"] + "-" + str(month) + "-" + str(day), "%Y-%m-%d")
                    putLog("Date format was wrong for pid (pid = records number), corrected for -2 days", n, "XML parcing" + gz, "format")
                data["pub_date"] = date
            for k, v in elem.attrib.iteritems():
                if k == "PubStatus":
                    month = childs["Month"]
                    if not re.match("\d", month):
                        month = months[childs["Month"]]
                    try:
                        date = datetime.strptime(childs["Year"] + "-" + str(month) + "-" + childs["Day"], "%Y-%m-%d")
                    except:
                        month = int(month)
                        day = int(childs["Day"])  # say, when 31 for Feb
                        if day > 30 and (month == 9 or month == 4 or month == 6 or month == 11):
                            day = day - 2
                        if day > 28 and month == 2:
                            day = day - 3
                        if day < 1:
                            day = 1
                        if int(childs["Year"]) == 1:
                            print str(pubmed) + " :pubmed: " + str(childs["Year"]) + "-" + str(month) + "-" + str(day)
                            childs["Year"] = 1900
                        try:
                            date = datetime.strptime(str(childs["Year"]) + "-" + str(month) + "-" + str(day), "%Y-%m-%d")
                        except:
                            print str(childs["Year"]) + "-" + str(month) + "-" + str(day)
                            date = datetime.strptime(str(childs["Year"]) + "-" + str(month) + "-" + str(28), "%Y-%m-%d")
                    if v == "received":
                        data["received_date"] = date
                    if v == "accepted":
                        data["accepted_date"] = date
                    if v == "pubmed":
                        if data["pub_date"] < datetime.strptime("1901-01-01", "%Y-%m-%d") or data["pub_date"] > datetime.now():
                            data["pub_date"] = date
                if k == "IdType" and v == "pubmed" and elem.tag == "ArticleId":
                    data["pubmed"] = 0
                    if elem.text is not None:
                        data["pubmed"] = int(elem.text)
                        pubmed = int(elem.text)
                if k == "IdType" and v == "doi" and elem.tag == "ArticleId":
                    data["doi"] = elem.text
                if k == "Source" and v == "ORCID" and elem.tag == "Identifier":
                    if re.search('http://orcid.org', elem.text):
                        a_data["orcid"] = elem.text
                    elif re.search('-', elem.text) and not re.search('http://orcid.org', elem.text):
                        a_data["orcid"] = 'http://orcid.org/' + elem.text
                    else:
                        a_data["orcid"] = 'http://orcid.org/' + elem.text[0:4] + "-" + elem.text[4:8] + "-" + elem.text[8:12] + "-" + elem.text[12:16]
                data["num_of_authors"] = len(ca_list)
            for k, v in names_p.iteritems():
                if k == elem.tag:
                    data[v] = elem.text
            if elem.tag == "Keyword":
                kw_list.append(elem.text)
                # print event, elem.tag, elem.attrib, '>', elem.text, '<', date  #, json
        if elem.tag == 'Author' and event == 'end':
            a_data["position"] = len(ca_list) + 1
            ca_list.append(a_data)
            a_data = {}
        if elem.tag == 'PubmedArticle' and event == 'end':
            data["authors"] = ca_list
            data["keywords"] = kw_list
            keys = {"pubmed": data["pubmed"]}
            paper = DBcall("papers", 0).findData(keys)
            if paper:
                data["xml_source_update"] = gz
                DBcall("papers", n).updateData(keys, data)
                updts += 1
            else:
                data["xml_source"] = gz
                DBcall("papers", n).loadData([data])
                insrts += 1
            p_data = {}
            data = {}
            ca_list = []
            kw_list = []
            n += 1
    nn += 1
    print str(datetime.now())[:-7] + " : finished updating " + str(nn) + "th " + xmL + " with " + str(updts) + " updates and " + str(insrts) + " inserts"
    # with open(xmL, 'rb') as f_in, gzip.open(xmL + '.gz', 'wb') as f_out:
    #     shutil.copyfileobj(f_in, f_out)
    os.unlink(xmL)
print str(datetime.now())[:-7] + " : done"
