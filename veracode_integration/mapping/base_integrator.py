#!/usr/bin/python
import sys, os

sys.path.append("/home/geoff/sde-lint/")

from sdelib.apiclient import APIBase
from sdelib.conf_mgr import config

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
        return None

    def apply_findings(self, project):
        self.api = APIBase(self.config)
        for finding in self.get_findings():
            task_id = self.map_finding( finding['cweid'] )
            filename = ''
            if finding.has_key('sourcefilepath'):
                filename=finding['sourcefilepath']
            if ( task_id == None or task_id == ''):
                print "ERROR: Could not map finding (cweid=%s,file=%s)" % (finding['cweid'], filename)
                continue
            ret_err,ret_val = self.api.add_note("%d-T%s" % (project, task_id), finding['description'], filename, "TODO")
            if ret_err:
                print "ERROR: Could not add TODO note to %d-T%s (cweid=%s,file=%s) Reason: %d-%s" % (project, task_id, finding['cweid'], filename, ret_err, ret_val)
            else:
                print "SUCCESS: TODO note added to %d-T%s (cweid=%s,file=%s)" % (project, task_id, finding['cweid'], filename)
        


def main(argv):
    ret = config.parse_args(argv)
    if not ret:
        sys.exit(1)

    base = BaseIntegrator(config)
    base.load_mapping_from_csv(config['targets'][0])
    base.output_mapping()

if __name__ == "__main__":
    main(sys.argv)

