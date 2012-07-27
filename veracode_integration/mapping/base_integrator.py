#!/usr/bin/python
import sys, os
import csv
import re
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sdelib.conf_mgr import config
from sdelib.interactive_plugin import PlugInExperience

class BaseIntegrator:
    def __init__(self, config):
        self.findings = []
        self.mapping = {}
        self.report_id = ""
        self.config = config
        self.plugin = PlugInExperience(config)

    def load_mapping_from_csv(self, csv_file):
        csv_mapping = {}
        mappingReader = csv.reader(open(csv_file),delimiter=',',quotechar='"')
        for row in mappingReader:
            csv_mapping[row[1]]=row[0]
        self.mapping = csv_mapping

    def get_findings(self):
        return self.findings

    def generate_findings(self):
        self.findings[:] = []

    def output_mapping(self):
        print self.mapping

    def output_findings(self):
        for item in self.findings:
            print '%5s,%5s,%5s,%s' % (item['issueid'], item['cweid'], item['categoryid'],item['description'][:120])

    def lookup_task(self, cwe_id):
        if(self.mapping.has_key(cwe_id)):
            return self.mapping[cwe_id]
        return None

    def log_message (self, severity, message):
        now = datetime.now().isoformat(' ')
        print "%s - %s - %s" % (now, severity, message)

    def save_findings(self, commit=True):

        stats_subtasks_added = 0
        stats_tasks_affected = 0
        stats_errors = 0
        stats_missing_maps = 0

        self.generate_findings()

        severityError = "ERROR"
        severityWarn = "WARN"
        severityMsg = "INFO"
        severityTestRun = "TEST_RUN"        

        self.log_message(severityMsg, "Integration underway: %s" % (self.report_id))

        for finding in self.get_findings():
            mapped_task_id = self.lookup_task( finding['cweid'] )
            file_name = ''
            if finding.has_key('source'):
                file_name=finding['source']
            if ( mapped_task_id == None or mapped_task_id == ''):
                self.log_message(severityWarn, "Could not map finding (cweid=%s,source=%s)" % (finding['cweid'], file_name))
                stats_missing_maps += 1
                continue

            task_id = "T%s" % (mapped_task_id)

            description  = "Analysis: %s\n\n" % (self.report_id)
            description += "CWE: http://cwe.mitre.org/data/definitions/%s.html\n\n" % (finding['cweid'])
            description += "Detail: %s\n" % (finding['description'][:255])
            if (finding.has_key('line')):
                description += "Line: %s" % (finding['line'])

            msg = "%s/%s/%s (cweid=%s,source=%s)" % (self.config['application'], self.config['project'], task_id, finding['cweid'], file_name)

            if commit:
                ret_err,ret_val = self.plugin.add_note(task_id, description, file_name, "TODO")
                if ret_err:
                    self.log_message(severityError, "Could not add TODO note to %s" % (msg))
                    stats_errors += 1
                else:
                    self.log_message(severityMsg, "TODO note added to %s" % (msg))
                    stats_subtasks_added += 1
            else:
                self.log_message(severityTestRun, "TODO note added to %s" % (msg))
                stats_subtasks_added += 1

        ret_err, ret_val = self.plugin.get_task_list()
        if ret_err:
            self.log_message(severityError,"Could not get task list for %s" % (self.config['project']))
            stats_errors += 1

        for task in ret_val:
           task_id = re.search('(\d+)-[^\d]+(\d+)', task['id']).group(2)

           msg = "%s/%s/%s" % (self.config['application'], self.config['project'], task_id)
           description = "Analysis: %s\n\nProcess completed" % (self.report_id)
           file_name = ''

           if commit:
               ret_err,ret_val = self.plugin.add_note("T%s" % (task_id), description, file_name, "DONE")
               if ret_err:
                   self.log_message(severityError, "Could not mark %s DONE (%s %s)" % (msg, ret_err, ret_val))
                   stats_errors += 1
               else:
                   self.log_message(severityMsg, "Marked %s task as DONE" % (msg))
                   stats_tasks_affected += 1
           else:
               self.log_message(severityTestRun, "Marked %s as DONE" % (msg))
               stats_tasks_affected += 1

        self.log_message(severityMsg, "---------------------------------------------------------")
        self.log_message(severityMsg, "%d subtasks created from %d flaws."%(stats_subtasks_added, len(self.get_findings())))
        self.log_message(severityMsg, "%d subtasks could not be created due to unknown mapping." %(stats_missing_maps))
        self.log_message(severityMsg, "%d errors encountered." % (stats_errors))
        self.log_message(severityMsg, "---------------------------------------------------------")
        self.log_message(severityMsg, "Completed")

def main(argv):
    ret = config.parse_args(argv)
    if not ret:
        sys.exit(1)

    base = BaseIntegrator(config)
    base.load_mapping_from_csv(config['targets'][0])
    base.output_mapping()

if __name__ == "__main__":
    main(sys.argv)

