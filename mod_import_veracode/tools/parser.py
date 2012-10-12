#!/usr/bin/python
import sys
from xml.dom import minidom

REQUIRED_ATTRIBS = ['issueid', 'cweid', 'categoryid', 'categoryname', 'description', 'severity', 'module']
LOCATION_ATTRIBS = ['sourcefilepath', 'sourcefile', 'line', 'location']

[u'cia_impact', u'inputvector', u'exploitdifficulty', u'module', u'date_first_occurrence', u'grace_period_expires', u'categoryid', u'categoryname', u'note', u'location', u'remediation_status', u'type', u'cvss', u'description', u'remediationeffort', u'exploitLevel', u'pcirelated', u'cweid', u'severity', u'count', u'issueid', u'capecid', u'affects_policy_compliance']

raw_findings = []

base = minidom.parse(sys.argv[1])
for node in base.getElementsByTagName('flaw'):
    entry = {}
    for attr in REQUIRED_ATTRIBS:
        if attr not in node.attributes.keys():
            raise 'Required attribute %s missing' % (attr)
        else:
            entry[attr] = node.attributes[attr].value
    raw_findings.append(entry)

for item in raw_findings:
    print '%5s,%5s,%5s' % (item['issueid'], item['cweid'], item['categoryid'])
    print item['description'][:120]

import pdb
pdb.set_trace()
