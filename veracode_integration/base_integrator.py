#!/usr/bin/python
import sys, os
import csv
import re
from datetime import datetime
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sdelib.commons import Error
from sdelib.conf_mgr import config
from sdelib.apiclient import APIError
from sdelib.interactive_plugin import PlugInExperience
from xml.dom import minidom

__all__ = ['BaseIntegrator, IntegrationError, IntegrationResult']

class IntegrationError(Error):
    pass

class IntegrationResult:
    def __init__(self):
        self.import_datetime=''
        self.total_unaffected_tasks=0
        self.total_affected_tasks=0
        self.error_count=0
        self.error_cwes_unmapped=0

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
        self.config.add_custom_option("logging", "Logging level: on | off", "l", "off")

    def parse_args(self, argv):
        ret = self.config.parse_args(argv)
        if not ret:
            raise IntegrationError("Error parsing arguments")
        self.init_plugin()

    def init_plugin(self):
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
        if(len(self.mapping) == 0):
            raise IntegrationError("No mapping was found in file '%s'" % config['mapping_file'])

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
        self.generate_findings()
        return self.findings

    def generate_findings(self):
        self.findings[:] = []

    def output_mapping(self):
        print self.mapping

    def unique_findings(self):
        """
        Return a map (task_id=> *flaw) based on list of findings (cwe)

        Where flaw is defined as:
            flaw[cwes]
            flaw[related_tasks]
        """
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
        if(self.mapping.has_key('*')):
            return self.mapping['*']
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
        if(config['logging'] == 'on'):
            now = datetime.now().isoformat(' ')
            print "%s - %s - %s" % (now, severity, message)

    def import_findings(self, commit):

        stats_subtasks_added = 0
        stats_tasks_affected = 0
        stats_api_errors = 0
        stats_missing_maps = 0
        stats_total_skips = 0
        stats_total_skips_findings = 0

        import_datetime = datetime.now().isoformat(' ')

        self.generate_findings()

        severityError = "ERROR"
        severityWarn = "WARN"
        severityMsg = "INFO"
        severityTestRun = "TEST_RUN"        

        self.log_message(severityMsg, "Integration underway for: %s" % (self.report_id))
        self.log_message(severityMsg, "Mapped application/project: %s/%s" % (self.config['application'],self.config['project']))
        self.log_message(severityMsg, "Unique import identifier: %s" % import_datetime)

        task_list = []
        tasks_found = []
        try:
            task_list = self.plugin.get_task_list()
        except APIError, e:
            self.log_message(severityError,"Could not get task list for %s - Reason: %s" % (self.config['project'], str(e)))
            stats_api_errors += 1

        unique_findings = self.unique_findings()
        missing_cwe_map = unique_findings['nomap']
        del unique_findings['nomap']

        task_ids = sorted(unique_findings.iterkeys())

        for task_id in task_ids:
            finding = unique_findings[task_id]

            if (not self.task_exists( task_id, task_list)):
                mapped_tasks = self.lookup_task("*")
                if(mapped_tasks <> None and len(mapped_tasks)>0):
                    new_task_id = mapped_tasks[0] # use the first one
                    if (task_id <> new_task_id):
                        self.log_message(severityWarn, "Task %s was not found in the project, mapping it to the default task %s." % (task_id, new_task_id))
                        task_id=new_task_id

            if (not self.task_exists( task_id, task_list)):
                self.log_message(severityError, "Task %s was not found in the project, skipping %d findings." % (task_id, len(finding['cwes'])))
                stats_total_skips += 1
                stats_total_skips_findings += len(finding['cwes'])
                continue

            task_id = "T%s" % (task_id)

            file_name = ''
            description  = "Update from external analysis: %s\n" % (self.report_id)
            description += "Imported on: %s\n\n" % (import_datetime)

            if (len(finding['cwes']) > 0):
                description += "Analysis did not complete successfully: %d flaws were identified related to this task. " % len(finding['cwes'])
                description += "The flaws are associated to the following common weakness:\n"
            else:
                description += "Analysis did not complete successfully: 1 flaw was identified that relates to this task. "
                description += "The flaw is associated to the common weakness:\n"
 
            for cwe in set(finding['cwes']):
                description += "http://cwe.mitre.org/data/definitions/"+cwe

            description = description[:500]

            msg = "%s" % task_id

            if commit:
                try:
                    api_result = self.plugin.add_note(task_id, description, file_name, "TODO")
                    self.log_message(severityMsg, "TODO note added to %s" % (msg))
                    stats_subtasks_added += 1
                except APIError, e:
                    self.log_message(severityError, "Could not add TODO note to %s - Reason: %s" % (msg, str(e)))
                    stats_api_errors += 1
            else:
                self.log_message(severityTestRun, "TODO note added to %s" % (msg))
                stats_subtasks_added += 1

        stats_noflaw_notes_added=0
        stats_test_tasks=0

        affected_tasks = []
        noflaw_tasks = []
        for task in task_list:
            if(task['phase'] in self.phase_exceptions):
                stats_test_tasks+=1
                continue

            task_id = re.search('(\d+)-[^\d]+(\d+)', task['id']).group(2)
            if(unique_findings.has_key(task_id)):
                affected_tasks.append(int(task_id))
                continue

            noflaw_tasks.append(int(task_id))

        noflaw_tasks = sorted(noflaw_tasks)

        for task_id in noflaw_tasks:

            msg = "T%s" % task_id
            description  = "Update from external analysis: %s\n" % (self.report_id)
            description += "Imported on: %s\n\n" % (import_datetime)
            description += "Analysis completed successfully: no flaws could be identified for this task."

            file_name = ''

            if commit:
                try:
                    self.plugin.add_note("T%s" % (task_id), description, file_name, "DONE")
                    self.log_message(severityMsg, "Marked %s task as DONE" % (msg))
                    stats_noflaw_notes_added += 1
                except APIError, e:
                    self.log_message(severityError, "Could not mark %s DONE - Reason: %s" % (msg, str(e)))
                    stats_api_errors += 1
            else:
                self.log_message(severityTestRun, "Marked %s as DONE" % (msg))
                stats_noflaw_notes_added += 1

        self.log_message(severityMsg, "---------------------------------------------------------")
        if (len(missing_cwe_map) > 0):
            self.log_message(severityError, "These CWEs could not be mapped: "+ ",".join(missing_cwe_map))
            self.log_message(severityError, "%d total flaws could not be mapped." %(len(missing_cwe_map)))
        else:
             self.log_message(severityMsg, "All CWEs successfully mapped to a task.")
        self.log_message(severityMsg, "%d subtasks created from %d flaws."%(stats_subtasks_added, len(self.findings)))
        self.log_message(severityMsg, "%d/%d project tasks had 0 flaws." %(len(noflaw_tasks),len(task_list)-(stats_test_tasks)))
        if (stats_total_skips > 0):
            self.log_message(severityError, "%d flaws were mapped to %d tasks not found in the project. Skipped"%(stats_total_skips_findings,stats_total_skips))
        self.log_message(severityMsg, "%d total api errors encountered." % (stats_api_errors))
        self.log_message(severityMsg, "---------------------------------------------------------")
        self.log_message(severityMsg, "Completed")

        result = IntegrationResult()
        result.import_datetime=import_datetime
        result.affected_tasks=affected_tasks
        result.noflaw_tasks=noflaw_tasks
        result.error_count=stats_api_errors
        result.error_cwes_unmapped=len(missing_cwe_map)
        return result

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

