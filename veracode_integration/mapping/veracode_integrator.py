#!/usr/bin/python
import sys
from base_integrator import BaseIntegrator
from sdelib.conf_mgr import config
from xml.dom import minidom

REQUIRED_ATTRIBS = ['issueid', 'cweid', 'categoryid', 'categoryname', 'description', 'severity', 'module']
LOCATION_ATTRIBS = ['sourcefilepath', 'sourcefile', 'line', 'location']

class VeracodeIntegrator(BaseIntegrator):

    def __init__(self, config):
        BaseIntegrator.__init__(self, config)
        self.raw_findings = []

    def parse(self, file_name):
        base = minidom.parse(file_name)
        for node in base.getElementsByTagName('flaw'):
            entry = {}
            for attr in REQUIRED_ATTRIBS:
                if attr not in node.attributes.keys():
                    raise Exception('Required attribute %s missing' % (attr))
                else:
                    entry[attr] = node.attributes[attr].value
            for attr in LOCATION_ATTRIBS:
                if attr in  node.attributes.keys():
                    entry[attr] = node.attributes[attr].value

            self.raw_findings.append(entry)

    def output_findings(self):
        for item in self.raw_findings:
            print '%5s,%5s,%5s' % (item['issueid'], item['cweid'], item['categoryid'])
            print item['description'][:120]

    def get_findings(self):
        return self.raw_findings

    def map_findings(self):
        for item in self.raw_findings:
            print '%5s,%5s,%5s,%5s' % (self.map_finding(item['cweid']), item['issueid'], item['cweid'], item['categoryid'])
            print item['description'][:120]

def main(argv):
    ret = config.parse_args(argv)
    if not ret:
        sys.exit(1)
    vcInt = VeracodeIntegrator(config)
    vcInt.load_mapping_from_csv(config['targets'][0])
    vcInt.output_mapping()
    vcInt.parse(config['targets'][1])
    vcInt.map_findings()
    vcInt.apply_findings(136)

if __name__ == "__main__":
    main(sys.argv)

