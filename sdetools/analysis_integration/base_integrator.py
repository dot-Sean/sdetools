#!/usr/bin/python
import collections
import re
import xml
import zipfile
from datetime import datetime
from xml.sax.handler import ContentHandler
from sdetools.extlib.defusedxml import minidom, sax

from sdetools.sdelib.commons import Error, abc
from sdetools.sdelib.restclient import APIError
from sdetools.sdelib.interactive_plugin import PlugInExperience

abstractmethod = abc.abstractmethod

from sdetools.sdelib import log_mgr
logger = log_mgr.mods.add_mod(__name__)

class IntegrationError(Error):
    pass

class IntegrationResult(object):
    def __init__(self, import_start_datetime, import_finish_datetime, affected_tasks, noflaw_tasks,
            error_count, error_weaknesses_unmapped):
        self.import_start_datetime = import_start_datetime
        self.import_finish_datetime = import_finish_datetime
        self.affected_tasks = affected_tasks
        self.noflaw_tasks = noflaw_tasks
        self.error_count = error_count
        self.error_weaknesses_unmapped = error_weaknesses_unmapped

class BaseContentHandler(ContentHandler):

    @abstractmethod
    def valid_content_detected(self):
        pass

class BaseImporter(object):

    def __init__(self):
        self.report_id = ""
        self.raw_findings = []
        
class BaseZIPImporter(BaseImporter):
    ARCHIVED_FILE_NAME = None
    MAX_SIZE_IN_MB = 300  # Maximum archived file size in MB
    MAX_MEMORY_SIZE_IN_MB = 50  # Python 2.5 and prior must be much more conservative

    def __init__(self):
        super(BaseZIPImporter, self).__init__()

    def process_archive(self, zip_archive, importer):
        try:
            results_archive = zipfile.ZipFile(zip_archive, "r")
        except zipfile.BadZipfile, e:
            raise IntegrationError("Error opening file (Bad file) %s" % (zip_archive))
        except zipfile.LargeZipFile, e:
            raise IntegrationError("Error opening file (File too large) %s" % (zip_archive))

        try:
            file_info = results_archive.getinfo(self.ARCHIVED_FILE_NAME)
        except KeyError, ke:
            raise IntegrationError("File (%s) not found in archive %s" % (self.ARCHIVED_FILE_NAME, zip_archive))

        # Python 2.6+ can open a ZIP file entry as a stream
        if hasattr(results_archive, 'open'):
        
            # Restrict the size of the file we will open
            if file_info.file_size > self.MAX_SIZE_IN_MB * 1024 * 1024:
                raise IntegrationError("File %s is larger than %s MB: %d bytes" %
                        (self.ARCHIVED_FILE_NAME, self.MAX_SIZE_IN_MB, file_info.file_size))

            try:
                results_file = results_archive.open(self.ARCHIVED_FILE_NAME)
            except KeyError, ke:
                raise IntegrationError("File (%s) not found in archive %s" % (self.ARCHIVED_FILE_NAME, zip_archive))

            importer.parse_file(results_file)

        # Python 2.5 and prior must open the file into memory
        else:
            # Restrict the size of the file we will open into RAM
            if file_info.file_size > self.MAX_MEMORY_SIZE_IN_MB * 1024 * 1024:
                raise IntegrationError("File %s is larger than %s MB: %d bytes" %
                        (self.ARCHIVED_FILE_NAME, self.MAX_MEMORY_SIZE_IN_MB, file_info.file_size))

            results_xml = results_archive.read(self.ARCHIVED_FILE_NAME)
            importer.parse_string(results_xml)
            
        self.report_id = importer.report_id
        self.raw_findings = importer.raw_findings            
        
class BaseXMLImporter(BaseImporter):

    def __init__(self):
        super(BaseXMLImporter, self).__init__()

    @abstractmethod
    def _get_content_handler(self):
        """
        Returns a customizable XML Reader that can extract information as
        the parse goes through the file
        """
        pass

    def parse(self, file_name):
        if isinstance(file_name, basestring):
            try:
                fp = open(file_name, 'r')
            except IOError, ioe:
                raise IntegrationError("Could not open file '%s': %s" % (file_name, ioe))
        else:
            fp = file_name
        self.parse_file(fp)

    def parse_file(self, xml_file):
        XMLReader = self._get_content_handler()
        try:    
            parser = sax.make_parser()
            parser.setContentHandler(XMLReader)
            parser.parse(xml_file)
        except (xml.sax.SAXException, xml.sax.SAXParseException, xml.sax.SAXNotSupportedException, 
                xml.sax.SAXNotRecognizedException), se:
            raise IntegrationError("Could not parse file '%s': %s" % (xml_file, se))

        if not XMLReader.valid_content_detected():
            raise IntegrationError("Malformed document detected: %s" % xml_file)

        self.raw_findings = XMLReader.raw_findings
        if XMLReader.report_id:
            self.report_id = XMLReader.report_id   
        
    def parse_string(self, xml):
        XMLReader = self._get_content_handler()
        try:    
            sax.parseString(xml, XMLReader)
        except (xml.sax.SAXException, xml.sax.SAXParseException, xml.sax.SAXNotSupportedException, 
                xml.sax.SAXNotRecognizedException), se:
            raise IntegrationError("Could not parse xml source %s" % (se))
        
        if not XMLReader.valid_content_detected():
            raise IntegrationError("Malformed document detected")

        self.raw_findings = XMLReader.raw_findings
        if XMLReader.report_id:
            self.report_id = XMLReader.report_id   

class BaseIntegrator(object):
    TOOL_NAME = 'External tool'

    def __init__(self, config, default_mapping_file=None):
        self.findings = []
        self.phase_exceptions = ['testing']
        self.mapping = {}
        self.report_id = "Not specified"
        self.config = config
        self.emit = self.config.emit
        self.weakness_title = {}
        self.confidence = {}
        self.plugin = PlugInExperience(self.config)
        self.config.add_custom_option("mapping_file",
                "Task ID -> Tool Weakness mapping in XML format", "m", default_mapping_file)
        self.config.add_custom_option("flaws_only",
                "Only update tasks identified having flaws. (True | False)", "z", "False")
        self.config.add_custom_option("trial_run",
                "Trial run only: 'True' or 'False'", "t", "False")

    def initialize(self):
        """
        This is a post init initialization. It needs to be called as the first
        function after configuration is processed (usually first call inside handler of
        the module)
        """
        self.config.process_boolean_config('flaws_only')
        self.config.process_boolean_config('trial_run')

    def load_mapping_from_xml(self):
        try:
            base = minidom.parse(self.config['mapping_file'])
        except KeyError, ke:
            raise IntegrationError("Missing configuration option 'mapping_file'")
        except Exception, e:
            raise IntegrationError("An error occurred opening mapping file '%s': %s" % (self.config['mapping_file'], e))

        weakness_mapping = collections.defaultdict(list)
        self.weakness_title = {}
        self.confidence = {}
        self.weakness_type = {}
        for task in base.getElementsByTagName('task'):
            if task.attributes.has_key('confidence'):
                self.confidence[task.attributes['id'].value] = task.attributes['confidence'].value

            for weakness in task.getElementsByTagName('weakness'):
                weakness_id = weakness.attributes['id'].value
                weakness_mapping[weakness_id].append(task.attributes['id'].value)
                self.weakness_type[weakness_id] = weakness.attributes['type'].value
                self.weakness_title[weakness_id] = weakness.attributes['title'].value

        self.mapping = weakness_mapping
        if not self.mapping:
            raise IntegrationError("No mapping was found in file '%s'" % self.config['mapping_file'])

    def generate_findings(self):
        return []

    def unique_findings(self):
        """
        Return a map (task_id=> *flaw) based on list of findings (weakness)

        Where flaw is defined as:
            flaw[weaknesses]
            flaw[related_tasks]
        """
        unique_findings = {'nomap': []}
        for finding in self.generate_findings():
            weakness_id = finding['weakness_id']
            mapped_tasks = self.lookup_task(weakness_id)
            if not mapped_tasks:
                unique_findings['nomap'].append(weakness_id)
                continue
            for mapped_task_id in mapped_tasks:
                if unique_findings.has_key(mapped_task_id):
                    flaws = unique_findings[mapped_task_id]
                else:
                    flaws = {'weaknesses': []}
                flaws['weaknesses'].append(finding)
                flaws['related_tasks'] = mapped_tasks
                unique_findings[mapped_task_id] = flaws
        return unique_findings

    def lookup_task(self, weakness_id):
        if self.mapping.has_key(weakness_id):
            return self.mapping[weakness_id]
        if self.mapping.has_key('*'):
            return self.mapping['*']
        return None

    def task_exists_in_project_tasks(self, task_id, project_tasks):
        """
        Return True if task_id is present in the array of project_tasks, False otherwise
        
        task_id is an integer
        project_tasks is an array of maps. Each map contains a key 'id' with a corresponding integer value
        """
        for task in project_tasks:
            task_search = re.search('^(\d+)-[^\d]+(\d+)$', task['id'])
            if task_search:
                project_task_id = task_search.group(2)
                if project_task_id == task_id:
                    return True
        return False

    def mapping_contains_task(self, needle_task_id):
        for task_id in self.mapping.values():
            if needle_task_id == task_id:
                return True
        return False

    def import_findings(self):
        stats_failures_added = 0
        stats_api_errors = 0
        stats_total_skips = 0
        stats_total_skips_findings = 0
        stats_total_flaws_found = 0
        import_start_datetime = datetime.now()

        logger.info("Integration underway for: %s" % (self.report_id))
        logger.info("Mapped SD application/project: %s/%s" % 
            (self.config['sde_application'], self.config['sde_project']))

        if self.config['trial_run']:
            logger.info("Trial run only. No changes will be made")
        else:
            ret = self.plugin.add_project_analysis_note(self.report_id, self.TOOL_NAME)
            project_analysis_note_ref = ret['id'] 

        task_list = self.plugin.get_task_list()
        logger.debug("Retrieved %d tasks from %s/%s" % 
            (len(task_list), self.config['sde_application'], self.config['sde_project']))

        unique_findings = self.unique_findings()
        missing_weakness_map = unique_findings['nomap']
        del unique_findings['nomap']

        task_ids = sorted(unique_findings.iterkeys())

        for task_id in task_ids:
            finding = unique_findings[task_id]

            if not self.task_exists_in_project_tasks( task_id, task_list):
                logger.debug("Task %s not found in project tasks" % task_id)
                mapped_tasks = self.lookup_task("*")
                if mapped_tasks:
                    new_task_id = mapped_tasks[0] # use the first one
                    if task_id != new_task_id:
                        logger.warn("Task %s was not found in the project, mapping it to the default task %s." % 
                                (task_id, new_task_id))
                        if not unique_findings.has_key(new_task_id):
                            unique_findings[new_task_id] = finding
                        else:
                            for weakness in finding['weaknesses']:
                                unique_findings[new_task_id]['weaknesses'].append(weakness)
                        del unique_findings[task_id]

        task_ids = sorted(unique_findings.iterkeys())

        for task_id in task_ids:
            finding = unique_findings[task_id]

            stats_total_flaws_found += len(finding['weaknesses'])

            if not self.task_exists_in_project_tasks(task_id, task_list):
                logger.error("Task %s was not found in the project, skipping %d findings." % 
                             (task_id, len(finding['weaknesses'])))
                stats_total_skips += 1
                stats_total_skips_findings += len(finding['weaknesses'])
                continue

            task_name = "T%s" % (task_id)

            analysis_findings = []
            last_weakness = None
            weakness_finding = {}

            for weakness in sorted(finding['weaknesses']):

                if 'description' in weakness:
                    weakness_description = weakness['description']
                elif (self.weakness_title.has_key(weakness['weakness_id']) and
                        self.weakness_title[weakness['weakness_id']] != ''):
                    weakness_description = self.weakness_title[weakness['weakness_id']]
                else:
                    weakness_description = weakness['weakness_id']

                if last_weakness != weakness_description:
                    if len(weakness_finding.items()) > 0:
                        analysis_findings.append(weakness_finding)
                        weakness_finding = {}
                    weakness_finding['count'] = 0

                    if (self.weakness_type.has_key(weakness['weakness_id']) and
                            self.weakness_type[weakness['weakness_id']] == 'cwe'):
                        weakness_finding['cwe'] = weakness['weakness_id']

                    weakness_finding['desc'] = weakness_description

                    last_weakness = weakness_description

                if 'count' in weakness:
                    weakness_finding['count'] += weakness['count']
                else:
                    weakness_finding['count'] += 1

            if len(finding.items()) > 0:
                analysis_findings.append(weakness_finding)

            try:
                finding_confidence = "low"
                if self.confidence.has_key(task_id):
                    finding_confidence = self.confidence[task_id]

                if not self.config['trial_run']:
                    ret = self.plugin.add_analysis_note(task_name, project_analysis_note_ref, 
                            finding_confidence, analysis_findings)
                logger.debug("Marked %s as FAILURE with %s confidence" % (task_name, finding_confidence))
                stats_failures_added += 1
            except APIError, e:
                logger.exception("Unable to mark %s as FAILURE - Reason: %s" % (task_name, str(e)))
                self.emit.error("API Error: Unable to mark %s as FAILURE. Skipping ..." % (task_name))
                stats_api_errors += 1

        stats_passes_added = 0
        stats_test_tasks = 0

        affected_tasks = []
        noflaw_tasks = []
        for task in task_list:
            if(task['phase'] in self.phase_exceptions):
                stats_test_tasks += 1
                continue
            task_search = re.search('^(\d+)-[^\d]+(\d+)$', task['id'])
            if task_search:
                task_id = task_search.group(2)
                if(unique_findings.has_key(task_id)):
                    affected_tasks.append(task_id)
                    continue
            noflaw_tasks.append(task_id)

        if not self.config['flaws_only']:
            for task_id in noflaw_tasks:

                task_name = "T%s" % task_id

                finding_confidence = "none"
                if self.confidence.has_key(task_id):
                    finding_confidence = self.confidence[task_id]
                else:
                    continue

                try:
                    if not self.config['trial_run']:
                        analysis_findings = []

                        self.plugin.add_analysis_note(task_name, project_analysis_note_ref, 
                                finding_confidence, analysis_findings)
                    logger.info("Marked %s as PASS with %s confidence" % (task_name, finding_confidence))
                    stats_passes_added += 1
                except APIError, e:
                    logger.exception("Unable to mark %s as PASS - Reason: %s" % (task_name, str(e)))
                    self.emit.error("API Error: Unable to mark %s as PASS. Skipping ..." % (task_name))
                    stats_api_errors += 1

        if missing_weakness_map:
            self.emit.error("Could not map %s flaws" % (len(missing_weakness_map)), 
                err_type='unmapped_weakness', 
                weakness_list=missing_weakness_map)
        else:
            self.emit.info("All flaws successfully mapped to tasks.")

        results = {}
        results['total_flaws_found'] = (stats_total_flaws_found, 'Total Flaw Types Found')
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
                                 error_weaknesses_unmapped=len(missing_weakness_map))
