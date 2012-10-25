#!/usr/bin/python
import collections
import re
from datetime import datetime

from sdelib.commons import Error
from sdelib.apiclient import APIError
from sdelib.interactive_plugin import PlugInExperience
from sdelib import log_mgr
from xml.dom import minidom

logger = log_mgr.mods.add_mod(__name__)

class IntegrationError(Error):
    pass

class IntegrationResult:
    def __init__(self, import_start_datetime, import_finish_datetime, affected_tasks, noflaw_tasks,
            error_count, error_cwes_unmapped):
        self.import_start_datetime = import_start_datetime
        self.import_finish_datetime = import_finish_datetime
        self.affected_tasks = affected_tasks
        self.noflaw_tasks = noflaw_tasks
        self.error_count = error_count
        self.error_cwes_unmapped = error_cwes_unmapped

class BaseIntegrator:
    def __init__(self, config):
        self.findings = []
        self.phase_exceptions = ['testing']
        self.mapping = {}
        self.report_id = ""
        self.config = config
        self.plugin = None
        self.cwe_title = {}
        self._init_config()

    def _init_config(self):
        self.config.add_custom_option("mapping_file",
                "Task ID -> CWE mapping in XML format", "m")
        self.config.add_custom_option("flaws_only",
                "Only update tasks identified having flaws. (on | off)", "z", "on")
        self.config.add_custom_option("trial_run",
                "Trial run only: 'true' or 'false' (default)", "t", "false")

    def parse_args(self, argv):
        ret = self.config.parse_args(argv)
        if not ret:
            raise IntegrationError("Error parsing arguments")
        self.init_plugin()

    def init_plugin(self):
        self.plugin = PlugInExperience(self.config)

    def load_mapping_from_xml(self):
        try:
            base = minidom.parse(self.config['mapping_file'])
        except KeyError, ke:
            raise IntegrationError("Missing configuration option 'mapping_file'")
        except Exception, e:
            raise IntegrationError("An error occurred opening mapping file '%s'" % self.config['mapping_file'])

        cwe_mapping = collections.defaultdict(list)
        self.cwe_title = {}
        for task in base.getElementsByTagName('task'):
            for cwe in task.getElementsByTagName('cwe'):
                cwe_id = cwe.attributes['id'].value
                cwe_mapping[cwe_id].append(task.attributes['id'].value)
                self.cwe_title[cwe_id] = cwe.attributes['title'].value

        self.mapping = cwe_mapping
        if not self.mapping:
            raise IntegrationError("No mapping was found in file '%s'" % self.config['mapping_file'])

    def generate_findings(self):
        return []

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
        for finding in self.generate_findings():
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

    def get_tool_name(self):
        return 'External tool'

    def import_findings(self):
        commit = (self.config['trial_run'] != 'true')

        stats_subtasks_added = 0
        stats_api_errors = 0
        stats_total_skips = 0
        stats_total_skips_findings = 0
        stats_total_flaws_found = 0
        import_start_datetime = datetime.now()
        file_name = '' # Needed for Notes API. All notes will have an empty filename.

        logger.info("Integration underway for: %s" % (self.report_id))
        logger.info("Mapped SD application/project: %s/%s" % (self.config['application'], self.config['project']))

        if not commit:
            logger.info("Trial run only. No changes will be made")

        task_list = []
        try:
            task_list = self.plugin.get_task_list()
            logger.debug("Retrieved task list for %s/%s" % (self.config['application'], self.config['project']))
        except APIError, e:
            logger.exception("Could not get task list for %s/%s - Reason: %s" % 
                (self.config['application'], self.config['project'], str(e)))
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
                        logger.warn("Task %s was not found in the project, mapping it to the default task %s." % (task_id, new_task_id))
                        task_id = new_task_id

            stats_total_flaws_found += len(finding['cwes'])

            if not self.task_exists(task_id, task_list):
                logger.error("Task %s was not found in the project, skipping %d findings." % (task_id, len(finding['cwes'])))
                stats_total_skips += 1
                stats_total_skips_findings += len(finding['cwes'])
                continue

            task_id = "T%s" % (task_id)

            description  = "Automated analysis tool %s identified %d potential vulnerabilities for this task.\n" % (self.get_tool_name(), len(finding['cwes']))
            description += "%s Reference: %s\n\n" % (self.get_tool_name(), self.report_id)
            description += "Referenced Weaknesses:\n"

            for cwe in sorted(set(finding['cwes'])):
                if self.cwe_title.has_key(cwe):
                   description += "CWE #%s: %s\n" % ( cwe, self.cwe_title[cwe] )
                else:
                   description += "CWE #%s\n" % ( cwe )

            description = description[:800]

            msg = "%s" % task_id

            if commit:
                try:
                    self.plugin.add_note(task_id, description, file_name, "TODO")
                    logger.debug("TODO note added to %s" % (msg))
                    stats_subtasks_added += 1
                except APIError, e:
                    logger.exception("Could not add TODO note to %s - Reason: %s" % (msg, str(e)))
                    stats_api_errors += 1
            else:
                logger.debug("TODO note added to %s" % (msg))
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

        if self.config['flaws_only'] == 'off':
            for task_id in noflaw_tasks:
                msg = "T%s" % task_id
                description  = "Automated analysis tool %s did not identify any potential vulnerabilities for this task.\n" % (self.get_tool_name())
                description += "%s Reference: %s\n\n" % (self.get_tool_name(), self.report_id)
    
                if commit:
                    try:
                        self.plugin.add_note("T%s" % (task_id), description, file_name, "DONE")
                        logger.debug("Marked %s task as DONE" % (msg))
                        stats_noflaw_notes_added += 1
                    except APIError, e:
                        logger.exception("Could not mark %s DONE - Reason: %s" % (msg, str(e)))
                        stats_api_errors += 1
                else:
                    logger.info("Marked %s as DONE" % (msg))
                    stats_noflaw_notes_added += 1

        logger.info("---------------------------------------------------------")
        if missing_cwe_map:
            logger.error("These CWEs could not be mapped: "+ ",".join(missing_cwe_map))
            logger.error("%d total flaws could not be mapped." %(len(missing_cwe_map)))
        else:
            logger.info("All CWEs successfully mapped to a task.")
        logger.info("%d subtasks created from %d flaws."%(stats_subtasks_added, stats_total_flaws_found))
        logger.info("%d/%d project tasks had 0 flaws." %(len(noflaw_tasks),len(task_list)-(stats_test_tasks)))
        if stats_total_skips:
            logger.error("%d flaws were mapped to %d tasks not found in the project. Skipped"%(stats_total_skips_findings,stats_total_skips))
        logger.info("%d total api errors encountered." % (stats_api_errors))
        logger.info("---------------------------------------------------------")
        logger.info("Completed")

        return IntegrationResult(import_start_datetime=import_start_datetime,
                                 import_finish_datetime=datetime.now(),
                                 affected_tasks=affected_tasks,
                                 noflaw_tasks=noflaw_tasks,
                                 error_count=stats_api_errors,
                                 error_cwes_unmapped=len(missing_cwe_map))
