#!/usr/bin/python
import sys, os
import collections
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
    def __init__(self, import_datetime, affected_tasks, noflaw_tasks,
            error_count, error_cwes_unmapped):
        self.import_datetime = import_datetime
        self.affected_tasks = affected_tasks
        self.noflaw_tasks = noflaw_tasks
        self.error_count = error_count
        self.error_cwes_unmapped = error_cwes_unmapped
        # TODO: Do we need / use these?
        # self.total_affected_tasks = 0
        # self.total_unaffected_tasks = 0

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
        self.config.add_custom_option("mapping_file",
                "Task ID -> CWE mapping in XML format", "m")
        self.config.add_custom_option("logging",
                "Logging level: on | off", "l", "off")
        self.config.add_custom_option("trial_run",
                "Trial run only: 'true' or 'false' (default)", "t", "false")

    def parse_args(self, argv):
        ret = self.config.parse_args(argv)
        if not ret:
            raise IntegrationError("Error parsing arguments")
        self.init_plugin()

    def init_plugin(self):
        # TODO: Should this be config, or self.config?
        self.plugin = PlugInExperience(config)

    def load_mapping_from_xml(self):
        try:
            base = minidom.parse(config['mapping_file'])
        except KeyError, ke:
            raise IntegrationError("Missing configuration option 'mapping_file'")
        except Exception, e:
            raise IntegrationError("An error occurred opening mapping file '%s'" % config['mapping_file'])

        cwe_mapping = collections.defaultdict(list)
        for task in base.getElementsByTagName('task'):
            for cwe in task.getElementsByTagName('cwe'):
                cwe_id = cwe.attributes['id'].value
                cwe_mapping[cwe_id].append(task.attributes['id'].value)

        self.mapping = cwe_mapping
        if not self.mapping:
            raise IntegrationError("No mapping was found in file '%s'" % config['mapping_file'])

    def load_mapping_from_csv(self):
        try:
            mapping_reader = csv.reader(open(csv_file),delimiter=',',quotechar='"')
        except KeyError, ke:
             raise IntegrationError("Missing configuration option 'mapping_file'")
        except Exception, e:
             raise IntegrationError("An error occured opening mapping file '%s'" % csv_file)

        csv_mapping = collections.defaultdict(list)
        for row in mapping_reader:
            # TODO: what is row[5]? what is row[3]?
            key = row[5]
            csv_mapping[key].append(row[3])
        self.mapping = csv_mapping

    def get_findings(self):
        # TODO: Do we really need get_findings() and generate_findings(). The
        #       later seems to be what we want. I'm also not a fan of get_xyz
        #       methods with side effects. Do we want to rebuild the findings
        #       everytime this is called?
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
        unique_findings = {'nomap': []}
        for finding in self.get_findings():
            cwe_id = finding['cweid']
            mapped_tasks = self.lookup_task(cwe_id)
            if not mapped_tasks:
                unique_findings['nomap'].append(cwe_id)
                continue
            for mapped_task_id in mapped_tasks:
                if unique_findings.has_key(mapped_task_id):
                    flaws = unique_findings[mapped_task_id]
                else:
                    flaws = {'cwes': []}
                flaws['cwes'].append(cwe_id)
                flaws['related_tasks'] = mapped_tasks
                unique_findings[mapped_task_id] = flaws
        return unique_findings

    def output_findings(self):
        for item in self.findings:
            print '%5s,%5s,%5s,%s' % (item['issueid'], item['cweid'], item['categoryid'],item['description'][:120])

    def lookup_task(self, cwe_id):
        if self.mapping.has_key(cwe_id):
            return self.mapping[cwe_id]
        if self.mapping.has_key('*'):
            return self.mapping['*']
        return None

    def task_exists(self, needle_task_id, haystack_tasks):
        for task in haystack_tasks:
            task_id = re.search('(\d+)-[^\d]+(\d+)', task['id']).group(2)
            if task_id == needle_task_id:
                return True
        return False

    def mapping_contains_task(self, needle_task_id):
        for task_id in self.mapping.values():
            if needle_task_id == task_id:
                return True
        return False

    def log_message (self, severity, message):
        # TODO: We should use python's built in logger.
        if config['logging'] == 'on':
            now = datetime.now().isoformat(' ')
            print "%s - %s - %s" % (now, severity, message)

    def import_findings(self):
        commit = (config['trial_run'] != 'true')

        stats_subtasks_added = 0
        stats_tasks_affected = 0
        stats_api_errors = 0
        stats_missing_maps = 0
        stats_total_skips = 0
        stats_total_skips_findings = 0
        import_datetime = datetime.now().isoformat(' ')

        self.generate_findings()

        # TODO: There must be a better place to declare these. When a sub
        #       class wants to log a message it would have to redeclare these
        #       values.
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
            self.log_message(severityError, "Could not get task list for %s - Reason: %s" % (self.config['project'], str(e)))
            stats_api_errors += 1

        unique_findings = self.unique_findings()
        missing_cwe_map = unique_findings['nomap']
        del unique_findings['nomap']

        task_ids = sorted(unique_findings.iterkeys())

        for task_id in task_ids:
            finding = unique_findings[task_id]

            if not self.task_exists( task_id, task_list):
                mapped_tasks = self.lookup_task("*")
                if mapped_tasks:
                    new_task_id = mapped_tasks[0] # use the first one
                    if task_id != new_task_id:
                        self.log_message(severityWarn, "Task %s was not found in the project, mapping it to the default task %s." % (task_id, new_task_id))
                        task_id = new_task_id

            if not self.task_exists(task_id, task_list):
                self.log_message(severityError, "Task %s was not found in the project, skipping %d findings." % (task_id, len(finding['cwes'])))
                stats_total_skips += 1
                stats_total_skips_findings += len(finding['cwes'])
                continue

            task_id = "T%s" % (task_id)

            description  = "Update from external analysis: %s\n" % (self.report_id)
            description += "Imported on: %s\n\n" % (import_datetime)
            if finding['cwes']:
                description += "Analysis did not complete successfully: %d flaws were identified related to this task. " % len(finding['cwes'])
                description += "The flaws are associated to the following common weakness:\n"
            else:
                description += "Analysis did not complete successfully: 1 flaw was identified that relates to this task. "
                description += "The flaw is associated to the common weakness:\n"

            for cwe in set(finding['cwes']):
                description += "http://cwe.mitre.org/data/definitions/" + cwe + "\n"

            description = description[:800]

            msg = "%s" % task_id

            if commit:
                file_name = ''  # Currently required to indicate note was created via API.
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

            file_name = ''  # Currently required to indicate note was created via API.
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
        if missing_cwe_map:
            self.log_message(severityError, "These CWEs could not be mapped: "+ ",".join(missing_cwe_map))
            self.log_message(severityError, "%d total flaws could not be mapped." %(len(missing_cwe_map)))
        else:
             self.log_message(severityMsg, "All CWEs successfully mapped to a task.")
        self.log_message(severityMsg, "%d subtasks created from %d flaws."%(stats_subtasks_added, len(self.findings)))
        self.log_message(severityMsg, "%d/%d project tasks had 0 flaws." %(len(noflaw_tasks),len(task_list)-(stats_test_tasks)))
        if stats_total_skips:
            self.log_message(severityError, "%d flaws were mapped to %d tasks not found in the project. Skipped"%(stats_total_skips_findings,stats_total_skips))
        self.log_message(severityMsg, "%d total api errors encountered." % (stats_api_errors))
        self.log_message(severityMsg, "---------------------------------------------------------")
        self.log_message(severityMsg, "Completed")

        return IntegrationResult(import_datetime=import_datetime,
                                 affected_tasks=affected_tasks,
                                 noflaw_tasks=noflaw_tasks,
                                 error_count=stats_api_errors,
                                 error_cwes_unmapped=len(missing_cwe_map))

def main(argv):
    base = BaseIntegrator(config)
    try:
        base.parse_args(argv)
    except:
        # TODO: We should catch an actual exception, or remove this code.
        sys.exit(1)

    base.load_mapping_from_xml()
    base.output_mapping()

if __name__ == "__main__":
    main(sys.argv)

