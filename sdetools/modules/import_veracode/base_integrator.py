#!/usr/bin/python
import collections
import re
from datetime import datetime
from xml.dom import minidom

from sdetools.sdelib.commons import Error
from sdetools.sdelib.restclient import APIError
from sdetools.sdelib.interactive_plugin import PlugInExperience

from sdetools.sdelib import log_mgr
logger = log_mgr.mods.add_mod(__name__)

class IntegrationError(Error):
    pass

class IntegrationResult(object):
    def __init__(self, import_start_datetime, import_finish_datetime, affected_tasks, noflaw_tasks,
            error_count, error_cwes_unmapped):
        self.import_start_datetime = import_start_datetime
        self.import_finish_datetime = import_finish_datetime
        self.affected_tasks = affected_tasks
        self.noflaw_tasks = noflaw_tasks
        self.error_count = error_count
        self.error_cwes_unmapped = error_cwes_unmapped

class BaseIntegrator(object):
    TOOL_NAME = 'External tool'

    def __init__(self, config, default_mapping_file=None):
        self.findings = []
        self.phase_exceptions = ['testing']
        self.mapping = {}
        self.report_id = ""
        self.config = config
        self.emit = self.config.emit
        self.plugin = None
        self.cwe_title = {}
        self.confidence = {}
        self.plugin = PlugInExperience(self.config)
        self.config.add_custom_option("mapping_file",
                "Task ID -> CWE mapping in XML format", "m", default_mapping_file)
        self.config.add_custom_option("flaws_only",
                "Only update tasks identified having flaws. (True | False)", "z", "True")
        self.config.add_custom_option("trial_run",
                "Trial run only: 'True' or 'False'", "t", "False")

    def load_mapping_from_xml(self):
        try:
            base = minidom.parse(self.config['mapping_file'])
        except KeyError, ke:
            raise IntegrationError("Missing configuration option 'mapping_file'")
        except Exception, e:
            raise IntegrationError("An error occurred opening mapping file '%s'" % self.config['mapping_file'])

        cwe_mapping = collections.defaultdict(list)
        self.cwe_title = {}
        self.confidence = {}
        for task in base.getElementsByTagName('task'):
            self.confidence[task.attributes['id'].value] = task.attributes['confidence'].value
            for cwe in task.getElementsByTagName('cwe'):
                cwe_id = cwe.attributes['id'].value
                cwe_mapping[cwe_id].append(task.attributes['id'].value)
                self.cwe_title[cwe_id] = cwe.attributes['title'].value

        self.mapping = cwe_mapping
        if not self.mapping:
            raise IntegrationError("No mapping was found in file '%s'" % self.config['mapping_file'])

    def generate_findings(self):
        return []

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

    def import_findings(self):
        commit = (self.config['trial_run'] != 'True')

        stats_failures_added = 0
        stats_api_errors = 0
        stats_total_skips = 0
        stats_total_skips_findings = 0
        stats_total_flaws_found = 0
        import_start_datetime = datetime.now()

        logger.info("Integration underway for: %s" % (self.report_id))
        logger.info("Mapped SD application/project: %s/%s" % 
            (self.config['sde_application'], self.config['sde_project']))

        if not commit:
            logger.info("Trial run only. No changes will be made")
        else:
            ret = self.plugin.add_project_analysis_note(self.report_id, self.TOOL_NAME)
            project_analysis_note_ref = ret['id'] 


        task_list = self.plugin.get_task_list()
        logger.debug("Retrieved task list for %s/%s" % 
            (self.config['sde_application'], self.config['sde_project']))

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

            task_name = "T%s" % (task_id)

            analysis_findings = []
            last_cwe = None
            cwe_finding = {}

            for cwe in sorted(finding['cwes']):
                if last_cwe != cwe:
                    if len(cwe_finding.items()) > 0:
                        analysis_findings.append(cwe_finding)
                        cwe_finding = {}
                    cwe_finding['count'] = 0
                    cwe_finding['cwe'] = cwe
                    last_cwe = cwe
                    if self.cwe_title.has_key(last_cwe):
                        cwe_finding['desc'] = self.cwe_title[last_cwe]

                cwe_finding['count'] = cwe_finding['count'] + 1

            if len(finding.items()) > 0:
                analysis_findings.append(cwe_finding)

            try:
                if commit:
                    finding_confidence = "none"
                    if self.confidence.has_key(task_id):
                        finding_confidence = self.confidence[task_id]

                    ret = self.plugin.add_analysis_note(task_name, project_analysis_note_ref, finding_confidence, analysis_findings)
                logger.debug("Marked %s as FAILURE with %s confidence" % (task_name, finding_confidence))
                stats_failures_added += 1
            except APIError, e:
                logger.exception("Unable to mark %s as FAILURE - Reason: %s" % (task_name, str(e)))
                self.emit.error("API Error: Unable to mark %s as FAILURE. Skipping ..." % (task_name))
                stats_api_errors += 1

        stats_passes_added=0
        stats_test_tasks=0

        affected_tasks = []
        noflaw_tasks = []
        for task in task_list:
            if(task['phase'] in self.phase_exceptions):
                stats_test_tasks+=1
                continue
            task_id = re.search('(\d+)-[^\d]+(\d+)', task['id']).group(2)
            if(unique_findings.has_key(task_id)):
                affected_tasks.append(task_id)
                continue
            noflaw_tasks.append(task_id)

        if self.config['flaws_only'] == 'False':
            for task_id in noflaw_tasks:

                task_name = "T%s" % task_id

                finding_confidence = "none"
                if self.confidence.has_key(task_id):
                    finding_confidence = self.confidence[task_id]
                else:
                    continue

                try:
                    if commit:
                        analysis_findings = []

                        self.plugin.add_analysis_note(task_name, project_analysis_note_ref, finding_confidence, analysis_findings)
                    logger.info("Marked %s as PASS with %s confidence" % (task_name, finding_confidence))
                    stats_passes_added += 1
                except APIError, e:
                    logger.exception("Unable to mark %s as PASS - Reason: %s" % (task_name, str(e)))
                    self.emit.error("API Error: Unable to mark %s as PASS. Skipping ..." % (task_name))
                    stats_api_errors += 1

        if missing_cwe_map:
            self.emit.error("Could not map %s flaws" % (len(missing_cwe_map)), err_type='unmapped_cwe', cwe_list=missing_cwe_map)
        else:
            self.emit.info("All flaws successfully mapped to tasks.")

        results = {}
        results['total_flaws_found'] = (stats_total_flaws_found, 'Total Flaws Found')
        results['tasks_marked_fail'] = (stats_failures_added, 'Number of Tasks marked as FAILED')
        results['tasks_without_findings'] = (noflaw_tasks, 'Number of Tasks in the project without any flaws')
        if stats_total_skips:
            results['skipped_flaws'] = (stats_total_skips_findings, 
                    'Number of flaws skipped because the related task was not'\
                    ' found in the project')
            results['skipped_tasks'] = (stats_total_skips, 'Number of tasks with flaws not found in project')

        # We queue the information to be sent along the close emit
        self.emit.queue(results=results)

        return IntegrationResult(import_start_datetime=import_start_datetime,
                                 import_finish_datetime=datetime.now(),
                                 affected_tasks=affected_tasks,
                                 noflaw_tasks=noflaw_tasks,
                                 error_count=stats_api_errors,
                                 error_cwes_unmapped=len(missing_cwe_map))
