db.papers.find({authors: {$elemMatch: {"last_name":"Ezaki", "initials":"H"}}},{pubmed:1,authors:1})

db.papers.ensureIndex({pubmed:1})
db.papers.ensureIndex({pub_date:1})
db.papers.ensureIndex({xml_source:1})
db.papers.ensureIndex({received_date:1})
db.papers.ensureIndex({title:1})
db.papers.ensureIndex({doi:1})
db.papers.ensureIndex({keywords:1})
