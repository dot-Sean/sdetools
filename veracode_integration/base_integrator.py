#!/usr/bin/python
import sys, os
import csv
import re
from datetime import datetime
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sdelib.commons import Error
from sdelib.conf_mgr import config
from sdelib.apiclient import APIError
from sdelib.interactive_plugin import PlugInExperience
from xml.dom import minidom

class IntegrationError(Error):
    pass

class BaseIntegrator:
    def __init__(self, config):
        self.findings = []
        self.phase_exceptions = ['testing']
        self.mapping = {}
        self.report_id = ""
        self.config = config
        self.plugin = None
        self._init_config()

    def _init_config(self):
        self.config.add_custom_option("mapping_file", "Task ID -> CWE mapping in XML format", "m")

    def parse_args(self, argv):
        ret = self.config.parse_args(argv)
        if not ret:
            raise IntegrationError("Error parsing arguments")
        self.plugin = PlugInExperience(config)

    def load_mapping_from_xml(self):
        try:
            base = minidom.parse(config['mapping_file'])
        except KeyError, ke:
            raise IntegrationError("Missing configuration option 'mapping_file'")
        except Exception, e:
            raise IntegrationError("An error occured opening mapping file '%s'" % config['mapping_file'])

        cwe_mapping = {}
        for task in base.getElementsByTagName('task'):
            for cwe in task.getElementsByTagName('cwe'):
                 tasks = []
                 if (cwe_mapping.has_key(cwe.attributes['id'].value)):
                     tasks = cwe_mapping[cwe.attributes['id'].value]
                 tasks.append(task.attributes['id'].value)
                 cwe_mapping[cwe.attributes['id'].value] = tasks

        self.mapping = cwe_mapping

    def load_mapping_from_csv(self):
        csv_mapping = {}
        try:
            mapping_reader = csv.reader(open(csv_file),delimiter=',',quotechar='"')
        except KeyError, ke:
             raise IntegrationError("Missing configuration option 'mapping_file'")
        except Exception, e:
             raise IntegrationError("An error occured opening mapping file '%s'" % csv_file)

        for row in mapping_reader:
            tasks = []
            if (csv_mapping.has_key(row[5])):
               tasks = csv_mapping[row[5]]
            tasks.append(row[3])
            csv_mapping[row[5]]=tasks
        self.mapping = csv_mapping

    def get_findings(self):
        return self.findings

    def generate_findings(self):
        self.findings[:] = []

    def output_mapping(self):
        print self.mapping

    def unique_findings(self):
        unique_findings = {}
        unique_findings['nomap'] = []
        for finding in self.get_findings():
            mapped_tasks = self.lookup_task( finding['cweid'] )
            file_name = ''
            if finding.has_key('source'):
                file_name=finding['source']
            if ( mapped_tasks == None or len(mapped_tasks) == 0):
                unique_findings['nomap'].append(finding['cweid'])
                continue

            flaws = {}
            for mapped_task_id in mapped_tasks:
                if(unique_findings.has_key(mapped_task_id)):
                    flaws = unique_findings[mapped_task_id]
                else:
                    flaws = {}
                    flaws['cwes'] = []
                    flaws['count'] = 0
                flaws['count'] += 1
                flaws['cwes'].append(finding['cweid'])
                flaws['related_tasks'] = mapped_tasks
                unique_findings[mapped_task_id]=flaws
        return unique_findings

    def output_findings(self):
        for item in self.findings:
            print '%5s,%5s,%5s,%s' % (item['issueid'], item['cweid'], item['categoryid'],item['description'][:120])

    def lookup_task(self, cwe_id):
        if(self.mapping.has_key(cwe_id)):
            return self.mapping[cwe_id]
        return None

    def task_exists(self, needle_task_id, haystack_tasks):
        for task in haystack_tasks:
            task_id = re.search('(\d+)-[^\d]+(\d+)', task['id']).group(2)
            if(task_id==needle_task_id):
                return True
        return False

    def mapping_contains_task(self, needle_task_id):
        for task_id in self.mapping.values():
            if(needle_task_id==task_id):
                return True
        return False

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
        self.log_message(severityMsg, "Mapped application/project: %s/%s" % (self.config['application'],self.config['project']))

        task_list = []
        tasks_found = []
        try:
            task_list = self.plugin.get_task_list()
        except APIError, e:
            self.log_message(severityError,"Could not get task list for %s - Reason: %s" % (self.config['project'], str(e)))
            stats_errors += 1

        unique_findings = self.unique_findings()
        missing_cwe_map = unique_findings['nomap']
        del unique_findings['nomap']

        stats_total_flaws = 0

        task_ids = sorted(unique_findings.iterkeys())

        for task_id in task_ids:
            finding = unique_findings[task_id]
            stats_total_flaws += finding['count']

            if (not self.task_exists( task_id, task_list)):
                self.log_message(severityMsg, "Task %s was not found in the project task list, skipping." % (task_id))
                continue

            task_id = "T%s" % (task_id)

            file_name = ''
            description  = "Analysis: %s\n\n" % (self.report_id)
            description += "Process completed with %d flaws found." % (finding['count'])

            msg = "%s" % task_id

            if commit:
                try:
                    self.plugin.add_note(task_id, description, file_name, "TODO")
                    self.log_message(severityMsg, "TODO note added to %s" % (msg))
                    stats_subtasks_added += 1
                except APIError, e:
                    self.log_message(severityError, "Could not add TODO note to %s - Reason: %s" % (msg, str(e)))
                    stats_errors += 1
            else:
                self.log_message(severityTestRun, "TODO note added to %s" % (msg))
                stats_subtasks_added += 1

        stats_unaffected_tasks=0
        stats_test_tasks=0

        task_ids = []
        for task in task_list:
            if(task['phase'] in self.phase_exceptions):
                stats_test_tasks+=1
                continue

            task_id = re.search('(\d+)-[^\d]+(\d+)', task['id']).group(2)
            if(unique_findings.has_key(task_id)):
                continue
           
            task_ids.append(int(task_id))

        task_ids = sorted(task_ids)

        for task_id in task_ids:
            stats_unaffected_tasks+=1

            msg = "T%s" % task_id
            description = "Analysis: %s\n\nProcess completed with 0 flaws found." % (self.report_id)
            file_name = ''

            if commit:
                try:
                    self.plugin.add_note("T%s" % (task_id), description, file_name, "DONE")
                    self.log_message(severityMsg, "Marked %s task as DONE" % (msg))
                    stats_tasks_affected += 1
                except APIError, e:
                    self.log_message(severityError, "Could not mark %s DONE - Reason: %s" % (msg, str(e)))
                    stats_errors += 1
            else:
                self.log_message(severityTestRun, "Marked %s as DONE" % (msg))
                stats_tasks_affected += 1

        self.log_message(severityError, "These CWEs could not be mapped: "+ ",".join(missing_cwe_map))
        self.log_message(severityMsg, "---------------------------------------------------------")
        self.log_message(severityMsg, "%d subtasks created from %d flaws."%(stats_subtasks_added, stats_total_flaws))
        self.log_message(severityMsg, "%d flaws could not be mapped." %(len(missing_cwe_map)))
        self.log_message(severityMsg, "%d errors encountered." % (stats_errors))
        self.log_message(severityMsg, "%d/%d project tasks had 0 flaws." %(stats_unaffected_tasks,len(task_list)-(stats_test_tasks)))
        self.log_message(severityMsg, "---------------------------------------------------------")
        self.log_message(severityMsg, "Completed")

def main(argv):
    base = BaseIntegrator(config)
    try:
        base.parse_args(argv)
    except:
        sys.exit(1)

    base.load_mapping_from_xml()
    base.output_mapping()

if __name__ == "__main__":
    main(sys.argv)

