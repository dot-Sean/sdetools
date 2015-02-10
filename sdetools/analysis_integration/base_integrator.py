#!/usr/bin/python
import collections
import re
import xml
import os
import glob
import zipfile
from datetime import datetime
from xml.sax.handler import ContentHandler
from sdetools.extlib.defusedxml import minidom, sax

from sdetools.sdelib.commons import Error, abc, UsageError
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


class BaseImporter(object):

    findings = []
    id = ""
    name = None

    def __init__(self):
        self.clear()

    def clear(self):
        self.findings = []
        self.id = ""
        self.name = None

    def can_parse_file(self):
        return False


class BaseContentHandler(ContentHandler, BaseImporter):

    def __init__(self):
        super(BaseContentHandler, self).__init__()

    @abstractmethod
    def valid_content_detected(self):
        pass


class BaseZIPImporter(BaseImporter):
    ARCHIVED_FILE_NAME = None
    MAX_NUMBER_ARCHIVED_FILES = 10
    MAX_SIZE_IN_MB = 300  # Maximum archived file size in MB
    MAX_MEMORY_SIZE_IN_MB = 50  # Python 2.5 and prior must be much more conservative
    IMPORTERS = {}
    PATTERN_IMPORTERS = {}
    available_importers = []
    detected_req_importer = None

    def __init__(self):
        super(BaseZIPImporter, self).__init__()
        self.available_importers = []
        self.clear()

    def clear(self):
        super(BaseZIPImporter, self).clear()
        self.IMPORTERS = {}
        self.PATTERN_IMPORTERS = {}
        self.detected_req_importer = None

    def register_importer(self, file_name, importer):
        self.IMPORTERS[file_name] = importer

    def register_importer_for_pattern(self, pattern, importer):
        self.PATTERN_IMPORTERS[pattern] = importer

    def detect_req_importer(self, report_file):
        """
        Examine all available importers scoped for this ZIP importer:
            - iterate over all zipped files
            - return the first importer that can open report_file
        """
        req_importer = None
        for item in self.available_importers:
            if req_importer:
                break

            self.clear()
            self.register_importer_for_pattern(item['pattern'], item['importer'])
            try:
                self.process_archive(report_file)
            except IntegrationError:
                # This is not the importer we're looking for
                continue

            for file_name, importer in self.IMPORTERS.items():
                if not req_importer and importer.get_parse_was_successful():
                    req_importer = importer
                importer.clear()

        self.detected_req_importer = req_importer
        return self.detected_req_importer

    def can_parse_file(self, report_file):
        try:
            results_archive = zipfile.ZipFile(report_file, "r")
        except zipfile.BadZipfile, zipfile.LargeZipFile:
            return False

        return self.detect_req_importer(report_file) is not None

    def process_archive(self, zip_archive):

        logger.debug("Processing archive file: %s" % zip_archive)

        try:
            results_archive = zipfile.ZipFile(zip_archive, "r")
        except zipfile.BadZipfile:
            raise IntegrationError("Error opening file (Bad file) %s" % zip_archive)
        except zipfile.LargeZipFile:
            raise IntegrationError("Error opening file (File too large) %s" % zip_archive)

        # Find any files in the ZIP that match any patterns
        for pattern in self.PATTERN_IMPORTERS.keys():
            for file_name in results_archive.namelist():
                if re.match(pattern, file_name):
                    self.register_importer(file_name, self.PATTERN_IMPORTERS[pattern])

        # Put a limit on the number of supported files we will process from a ZIP
        if len(self.IMPORTERS.keys()) > self.MAX_NUMBER_ARCHIVED_FILES:
            raise IntegrationError("File %s exceeds the limit of %d files" % (zip_archive,
                                                                              self.MAX_NUMBER_ARCHIVED_FILES))

        for file_name in self.IMPORTERS.keys():
            try:
                self._process_archived_file(results_archive, file_name)
            except IntegrationError, ie:
                raise IntegrationError("Error processing %s: %s" % (zip_archive, str(ie)))

        results_archive.close()

    def _process_archived_file(self, archive, file_name):

        logger.debug("Processing archived file: %s" % file_name)

        if file_name not in self.IMPORTERS:
            raise IntegrationError("No importer available for %s" % file_name)

        try:
            file_info = archive.getinfo(file_name)
        except KeyError:
            raise IntegrationError("File %s not found" % file_name)

        importer = self.IMPORTERS[file_name]

        # Python 2.6+ can open a ZIP file entry as a stream
        if hasattr(archive, 'open'):

            # Restrict the size of the file we will open
            if file_info.file_size > self.MAX_SIZE_IN_MB * 1024 * 1024:
                raise IntegrationError("File %s is larger than %s MB: %d bytes" %
                                       (file_name, self.MAX_SIZE_IN_MB, file_info.file_size))

            try:
                results_file = archive.open(file_name)
            except KeyError:
                raise IntegrationError("File %s not found" % file_name)

            importer.parse_file(results_file)

            results_file.close()

        # Python 2.5 and prior must open the file into memory
        else:
            # Restrict the size of the file we will open into RAM
            if file_info.file_size > self.MAX_MEMORY_SIZE_IN_MB * 1024 * 1024:
                raise IntegrationError("File %s is larger than %s MB: %d bytes" %
                                      (file_name, self.MAX_MEMORY_SIZE_IN_MB, file_info.file_size))

            results_xml = archive.read(file_name)
            importer.parse_string(results_xml)

        # retain the results in the importer
        self.IMPORTERS[file_name] = importer

    def parse(self, zip_file):
        self.process_archive(zip_file)
        build_ids = []
        for file_name in self.IMPORTERS.keys():
            self.findings.extend(self.IMPORTERS[file_name].findings)
            if self.IMPORTERS[file_name].id not in build_ids:
                build_ids.append(self.IMPORTERS[file_name].id)
        self.id = ', '.join(build_ids)


class BaseXMLImporter(BaseImporter):

    def __init__(self):
        super(BaseXMLImporter, self).__init__()
        self.last_parse_indicator = False

    @abstractmethod
    def _get_content_handler(self):
        """
        Returns a customizable XML Reader that can extract information as
        the parser goes through the file
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
        fp.seek(0)
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

        self.last_parse_indicator = XMLReader.valid_content_detected()

        if not XMLReader.valid_content_detected():
            raise IntegrationError("Malformed document detected: %s" % xml_file)

        self.findings = XMLReader.findings
        if XMLReader.id:
            self.id = XMLReader.id

    def parse_string(self, xml):
        XMLReader = self._get_content_handler()
        try:
            sax.parseString(xml, XMLReader)
        except (xml.sax.SAXException, xml.sax.SAXParseException, xml.sax.SAXNotSupportedException,
                xml.sax.SAXNotRecognizedException), se:
            raise IntegrationError("Could not parse xml source %s" % (se))

        self.last_parse_indicator = XMLReader.valid_content_detected()

        if not XMLReader.valid_content_detected():
            raise IntegrationError("Malformed document detected")

        self.findings = XMLReader.findings
        if XMLReader.id:
            self.id = XMLReader.id

    def get_parse_was_successful(self):
        return self.last_parse_indicator

    def can_parse_file(self, xml_file):
        try:
            self.parse(xml_file)
        except IntegrationError:
            return False

        self.findings = []
        self.id = None
        return self.last_parse_indicator


class BaseIntegrator(object):
    TOOL_NAME = 'External tool'
    AVAILABLE_IMPORTERS = [] # Subclasses must fill this list
    VALID_IMPORT_BEHAVIOUR = ['replace', 'replace-scanner', 'combine']

    # An internal map of possible verification and acceptable status meanings
    VALID_VERIFICATION_MAP = {'pass': ['TODO', 'DONE'], 'partial': ['TODO', 'DONE'], 'fail': ['TODO']}

    def __init__(self, config, tool_name, supported_file_types=[], default_mapping_file=None):
        self.findings = []
        self.phase_exceptions = ['testing']
        self.mapping = {}
        self.report_id = "Not specified"
        self.config = config
        self.emit = self.config.emit
        self.behaviour = 'replace'
        self.weakness_map_identifier = 'id'  # default XML attribute with weakness identifier
        self.weakness_title = {}
        self.confidence = {}
        self.taskstatuses = {}
        self.plugin = PlugInExperience(self.config)
        self.supported_file_types = supported_file_types

        if supported_file_types:
            self.config.opts.add(
                    "report_file",
                    "Common separated list of %s Report Files" % tool_name.capitalize(),
                    "x", None)
            self.config.opts.add(
                    "report_type",
                    "%s Report Type: %s|auto" % (tool_name.capitalize(), ', '.join(supported_file_types)),
                    default="auto")
        self.config.opts.add(
                "mapping_file",
                "Task ID -> Tool Weakness mapping in XML format",
                "m", default_mapping_file)
        self.config.opts.add(
                "import_behaviour",
                "One of the following: %s" % ', '.join(BaseIntegrator.VALID_IMPORT_BEHAVIOUR),
                default="replace")
        self.config.opts.add('task_status_mapping',
                'Update task status based on verification. Provide a mapping of (%s) to a task status slug'
                '(JSON encoded dictionary of strings)' % ', '.join(self.VALID_VERIFICATION_MAP.keys()),
                default='')
        self.config.opts.add("flaws_only", "Only update tasks identified having flaws. (True | False)", "z", "False")
        self.config.opts.add("trial_run", "Trial run only: (True | False)", "t", "False")

    def initialize(self):
        """
        This is a post init initialization. It needs to be called as the first
        function after configuration is processed (usually first call inside handler of
        the module)
        """
        self.config.process_boolean_config('flaws_only')
        self.config.process_boolean_config('trial_run')
        self.config.process_json_str_dict('task_status_mapping')

        if self.config['import_behaviour'] in BaseIntegrator.VALID_IMPORT_BEHAVIOUR:
            self.behaviour = self.config['import_behaviour']
        else:
            raise UsageError('Invalid import_behaviour %s' % self.config['import_behaviour'])

        if self.config['task_status_mapping']:
            # Get the available system task statuses and their meanings
            self._setup_taskstatuses()

            # Validate the mapping against the available system statuses
            # Sanity check the mapping
            #     - pass, partial may mark tasks with a status having meaning TODO or DONE only
            #     - fail may mark tasks with a status having meaning TODO only.
            for verification, status_name in self.config['task_status_mapping'].iteritems():
                if verification not in self.VALID_VERIFICATION_MAP:
                    raise UsageError('Invalid task_status_mapping verification %s' % verification)

                if status_name not in self.taskstatuses:
                    raise UsageError('Invalid task_status_mapping status "%s" for verification "%s"' %
                                     (status_name, verification))

                if self.taskstatuses[status_name]['meaning'] not in self.VALID_VERIFICATION_MAP[verification]:
                        raise UsageError('Unexpected task_status_mapping status "%s" for verification "%s"' %
                                         (status_name, verification))

        # Validate the report_type config. If report_type is not auto, we will process only
        # the specified report_type, else we process all supported file types.
        if self.supported_file_types:
            if self.config['report_type'] in self.supported_file_types:
                self.supported_file_types = [self.config['report_type']]
            elif self.config['report_type'] != 'auto':
                raise UsageError('Invalid report_type %s' % self.config['report_type'])

            self.process_report_file_config()

    def _setup_taskstatuses(self):
        statuses = self.plugin.get_taskstatuses()
        for status in statuses['taskstatuses']:
            self.taskstatuses[status['slug']] = status

    def detect_importer(self, report_file):
        for item in self.AVAILABLE_IMPORTERS:
            if item['importer'].can_parse_file(report_file):
                return item['importer']
        return None

    @staticmethod
    def _get_file_extension(file_path):
        return os.path.splitext(file_path)[1][1:]

    @abstractmethod
    def parse_report_file(self, report_file, report_type):
        """ Returns the raw findings and the report id for a single report file """

        return [], None

    def set_tool_name(self, tool_name):
        self.TOOL_NAME = tool_name

    def parse(self):
        _raw_findings = []
        _report_ids = []

        for report_file in self.config['report_file']:
            if self.config['report_type'] == 'auto':
                if not isinstance(report_file, basestring):
                    raise UsageError("On auto-detect mode, the file name needs to be specified.")
                report_type = self._get_file_extension(report_file)
            else:
                report_type = self.config['report_type']

            raw_findings, report_id = self.parse_report_file(report_file, report_type)

            _raw_findings.extend(raw_findings)

            if report_id:
                _report_ids.append(report_id)

        self.findings = _raw_findings

        if _report_ids:
            self.report_id = ', '.join(_report_ids)
        else:
            self.report_id = "Not specified"
            self.emit.info("Report ID not found in report: Using default.")

    def process_report_file_config(self):
        """
        If report files contains a directory path, find all possible files in that folder
        """
        if not self.config['report_file']:
            raise UsageError("Missing configuration option 'report_file'")

        if not isinstance(self.config['report_file'], basestring):
            # Should be a file object
            self.config['report_file'] = [self.config['report_file']]
        else:
            processed_report_files = []

            for file_path in self.config['report_file'].split(','):
                file_path = file_path.strip()
                file_name, file_ext = os.path.splitext(file_path)
                file_ext = file_ext[1:]

                if file_ext in self.supported_file_types:
                    processed_report_files.extend(glob.glob(file_path))
                elif re.search('[*?]', file_ext):
                    # Run the glob and filter out unsupported file types
                    processed_report_files.extend([f for f in glob.iglob(file_path)
                                                  if self._get_file_extension(f) in self.supported_file_types])
                elif not file_ext:
                    # Glob using our supported file types
                    if os.path.isdir(file_path):
                        _base_path = file_path + '/*'
                    else:
                        _base_path = file_name
                    for file_type in self.supported_file_types:
                        processed_report_files.extend(glob.glob('%s.%s' % (_base_path, file_type)))
                else:
                    raise UsageError('%s does not match any supported file type(s): %s' %
                                     (file_path, self.supported_file_types))
            if not processed_report_files:
                raise UsageError("Did not find any report files. Check if 'report_file' is configured properly.")
            else:
                self.config['report_file'] = processed_report_files

    def load_mapping_from_xml(self):
        try:
            base = minidom.parse(self.config['mapping_file'])
        except KeyError:
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
                weakness_id = weakness.attributes[self.weakness_map_identifier].value
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
        if '*' in self.mapping:
            return self.mapping['*']
        return None

    def task_exists_in_project_tasks(self, task_id, project_tasks):
        """
        Return True if task_id is present in the array of project_tasks, False otherwise

        task_id is an integer
        project_tasks is an array of maps. Each map contains a key 'id' with a corresponding integer value
        """
        for task in project_tasks:
            task_search = re.search('^(\d+)-T(\d+)$', task['id'])
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

        logger.info("Integration underway for: %s" % self.report_id)
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

            if not self.task_exists_in_project_tasks(task_id, task_list):
                logger.debug("Task %s not found in project tasks" % task_id)
                mapped_tasks = self.lookup_task("*")
                if mapped_tasks:
                    new_task_id = mapped_tasks[0]  # use the first one
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

            task_name = "T%s" % task_id

            analysis_findings = []
            last_weakness = None
            weakness_finding = {}

            for weakness in sorted(finding['weaknesses']):

                if 'description' in weakness:
                    weakness_description = weakness['description']
                elif (weakness['weakness_id'] in self.weakness_title and
                        self.weakness_title[weakness['weakness_id']] != ''):
                    weakness_description = self.weakness_title[weakness['weakness_id']]
                else:
                    weakness_description = weakness['weakness_id']

                if last_weakness != weakness_description:
                    if len(weakness_finding.items()) > 0:
                        analysis_findings.append(weakness_finding)
                        weakness_finding = {}
                    weakness_finding['count'] = 0

                    if (weakness['weakness_id'] in self.weakness_type and
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
                if task_id in self.confidence:
                    finding_confidence = self.confidence[task_id]

                if not self.config['trial_run']:
                    ret = self.plugin.add_analysis_note(task_name, project_analysis_note_ref,
                            finding_confidence, analysis_findings, self.behaviour, self.config['task_status_mapping'])
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
            if task['phase'] in self.phase_exceptions:
                stats_test_tasks += 1
                continue
            task_search = re.search('^(\d+)-T(\d+)$', task['id'])
            if task_search:
                task_id = task_search.group(2)
                if unique_findings.has_key(task_id):
                    affected_tasks.append(task_id)
                    continue
                noflaw_tasks.append(task_id)

        if not self.config['flaws_only']:
            for task_id in noflaw_tasks:

                task_name = "T%s" % task_id

                finding_confidence = "low"
                if task_id in self.confidence:
                    finding_confidence = self.confidence[task_id]
                else:
                    # We have no requirement coverage for this task
                    continue

                try:
                    if not self.config['trial_run']:
                        analysis_findings = []

                        self.plugin.add_analysis_note(task_name, project_analysis_note_ref,
                                finding_confidence, analysis_findings, self.behaviour,
                                self.config['task_status_mapping'])
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


