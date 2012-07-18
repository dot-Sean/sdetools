#!/usr/bin/pythona
import sys, os

sys.path.append("/home/geoff/sde-lint/")

from sdelib.apiclient import APIBase

import csv

class BaseIntegrator:
    def __init__(self, config):
        self.findings = []
        self.mapping = {}
        self.config = config

    def load_mapping_from_csv(self, csv_file):
        csv_mapping = {}
        mappingReader = csv.reader(open(csv_file),delimiter=',',quotechar='"')
        for row in mappingReader:
            csv_mapping[row[1]]=row[0]
        self.mapping = csv_mapping

    def get_findings(self):
        return self.findings

    def output_mapping(self):
        print self.mapping

    def output_findings(self):
        for item in self.findings:
            print '%5s,%5s,%5s,%s' % (item['issueid'], item['cweid'], item['categoryid'],item['description'][:120])

    def map_finding(self, cwe_id):
        if(self.mapping.has_key(cwe_id)):
            return self.mapping[cwe_id]
        return 'NOT_FOUND'

    def apply_findings(self, project, username, password):
        self.api = APIBase(self.config)
        for finding in self.get_findings():
            task_id = self.map_finding( finding['cweid'] )
            if ( task_id == 'NOT_FOUND'):
                continue
            filename = None
            if finding.has_key('sourcefilepath'):
                filename=finding['sourcefilepath']
            self.api.add_note("%d-T%s" % (project, task_id), finding['description'], filename, "TODO")        
        


def main(argv):
    base = BaseIntegrator({},{'method':'https','server':'newcastle.sdelements.com','debug_level':3,'username':'geoff@sdelements.com','password':'xxxxxxx'})
    base.load_mapping_from_csv(argv[1])
    base.output_mapping()

if __name__ == "__main__":
    main(sys.argv)

