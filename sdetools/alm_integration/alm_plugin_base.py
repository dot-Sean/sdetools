from datetime import datetime
from string import Template
import sys
import re

from sdetools.sdelib.commons import abc
abstractmethod = abc.abstractmethod

from sdetools.sdelib.commons import Error
from sdetools.sdelib.commons import UsageError
from sdetools.sdelib.restclient import APIError
from sdetools.sdelib.interactive_plugin import PlugInExperience

from sdetools.sdelib import log_mgr
logger = log_mgr.mods.add_mod(__name__)

RE_CODE_DOWNLOAD = re.compile(r'\{\{ USE_MEDIA_URL \}\}([^\)]+\))\{@class=code-download\}')
RE_TASK_IDS = re.compile('^[^\d]+\d+$')
RE_MAP_RANGE_KEY = re.compile('^([1-9]|10)(-([1-9]|10))?$')
PUBLIC_TASK_CONTENT = ('Visit us at http://www.sdelements.com/ to find out how you can easily add project-specific '
                       'software security requirements to your existing development processes.')


class AlmException(Error):
    """ Class for ALM Exceptions """

    def __init__(self, value):
        self.value = value

    def __str__(self):
        return str(self.value)


class AlmTask(object):
    """
    Abstract base class to represent a task in an ALM. This should be subclassed 
    by an implementation for a specific ALM that can translate the ALM fields to 
    SDE fields. For example, the ALM might use 'severity' while SD Elements uses 
    'priority'
    """

    @abstractmethod
    def get_task_id(self):
        """ Returns an ID string compatible with SD Elements """
        pass

    @abstractmethod
    def get_alm_id(self):
        """ Returns a unique identifier for the task in the ALM system """
        pass

    @abstractmethod
    def get_status(self):
        """ Returns a status compatible with SD Elements """
        pass

    @abstractmethod
    def get_timestamp(self):
        """ Returns a datetime.datetime object of last modified time """
        pass


class AlmConnector(object):
    """
    Abstract base class for connectors to Application Lifecycle
    Management tools such as JIRA, Team Foundation Server, Rally, etc.
    """
    # This needs to be overwritten
    alm_name = 'ALM Module'
    ALM_PRIORITY_MAP = 'alm_priority_map'
    VERIFICATION_STATUSES = ['none', 'partial', 'pass', 'fail']
    TEST_OPTIONS = ['server', 'project', 'settings']
    STANDARD_STATUS_LIST = ['TODO', 'DONE', 'NA']
    FIELD_OPTIONS = ['task_id', 'title', 'context', 'application', 'project']
    DEFAULT_TITLE_FORMAT = '${task_id} ${title}'
    default_priority_map = None
    feature_custom_lookup = False  # Assume the connector does not support custom lookups

    # This is an abstract base class
    __metaclass__ = abc.ABCMeta

    def __init__(self, config, alm_plugin):
        """  Initialization of the Connector

        Keyword arguments:
        sde_plugin -- An SD Elements Plugin configuration object
        alm_plugin -- A plugin to connect to the ALM tool
        """
        self.config = config
        self.ignored_tasks = []
        self.sde_plugin = PlugInExperience(self.config)
        self.alm_plugin = alm_plugin
        self._add_alm_config_options()
        self.emit = self.config.emit

    def _add_alm_config_options(self):
        """ Adds ALM config options to the config file"""
        self.config.opts.add('alm_phases', 'Phases to sync '
                '(comma separated list, e.g. requirements,testing)',
                default='requirements,architecture-design,development')
        self.config.opts.add('sde_statuses_in_scope', 'SDE statuses for adding to %s '
                '(comma separated %s)' % (self.alm_name, ','.join(AlmConnector.STANDARD_STATUS_LIST)),
                default='TODO')
        self.config.opts.add('sde_min_priority', 'Minimum SDE priority in scope',
                default='7')
        self.config.opts.add('sde_tags_filter', 'Filter project tasks by tag (tag1, tag2)',
                default='')
        self.config.opts.add('sde_verification_filter', 'Filter project tasks by verification statuses. Valid statuses '
                'are: ' + ', '.join(AlmConnector.VERIFICATION_STATUSES),
                default='')
        self.config.opts.add('how_tos_in_scope', 'Whether or not HowTos should be included',
                default='False')
        self.config.opts.add('selected_tasks', 'Optionally limit the sync to certain tasks '
                '(comma separated, e.g. T12,T13). Note: Overrides other selections.',
                default='')
        self.config.opts.add('alm_project', 'Project in %s' % self.alm_name,
                default='')
        self.config.opts.add('conflict_policy', 'Conflict policy to use',
                default='alm')
        self.config.opts.add('alm_context', 'Add additional context to issues created in %s' % self.alm_name,
                default='')
        self.config.opts.add('start_fresh', 'Delete any matching issues in %s' % self.alm_name,
                default='False')
        self.config.opts.add('show_progress', 'Show progress',
                default='False')
        self.config.opts.add('alm_title_format', 'Task title format in %s. May be composed of: %s' %
                (self.alm_name, ','.join(AlmConnector.FIELD_OPTIONS)),
                default=AlmConnector.DEFAULT_TITLE_FORMAT)
        self.config.opts.add('test_alm', 'Test Alm "server", "project" or "settings" '
                'configuration only',
                default='')
        self.config.opts.add('alm_standard_workflow', 'Standard workflow in ALM?',
                default='True')
        self.config.opts.add('alm_custom_fields', 
                'Customized fields to include when creating a task in %s '
                '(JSON encoded dictionary of strings)' % self.alm_name,
                default='')

        if self.feature_custom_lookup:
            self.config.opts.add('alm_custom_lookup_fields',
                    'Custom fields and values to use when finding a task in %s '
                    '(JSON encoded dictionary of strings)' % self.alm_name,
                    default='')

        if self.default_priority_map:
            self.config.opts.add(self.ALM_PRIORITY_MAP, 'Customized map from priority in SDE to %s '
                '(JSON encoded dictionary of strings)' % self.alm_name,
                default='')

    def initialize(self):
        """
        Verify that the configuration options are set properly
        """

        # Note: This will consider space as empty due to strip
        # We do this before checking if the config is non-empty later
        self.config.process_list_config('selected_tasks')
        for task in self.config['selected_tasks']:
            if not RE_TASK_IDS.match(task):
                raise UsageError('Invalid Task ID: %s' % task)

        self.config.process_list_config('sde_verification_filter')
        for verification_status in self.config['sde_verification_filter']:
            if verification_status not in AlmConnector.VERIFICATION_STATUSES:
                raise UsageError('Invalid status specified in sde_verification_filter: %s' % verification_status)

        if not self.config['selected_tasks']:
            self.config.process_list_config('alm_phases')
            if not self.config['alm_phases']:
                raise AlmException('Missing alm_phases in configuration')

            self.config.process_list_config('sde_statuses_in_scope')
            if not self.config['sde_statuses_in_scope']:
                raise AlmException('Missing the SD Elements statuses in scope')

            for status in self.config['sde_statuses_in_scope']:
                if status not in AlmConnector.STANDARD_STATUS_LIST:
                    raise AlmException('Invalid status specified in sde_statuses_in_scope')

            self.config.process_list_config('sde_tags_filter')

        if (not self.config['conflict_policy'] or
            not (self.config['conflict_policy'] == 'alm' or
                 self.config['conflict_policy'] == 'sde' or
                 self.config['conflict_policy'] == 'timestamp')):
            raise AlmException('Missing or incorrect conflict_policy '
                               'in configuration. Valid values are '
                               'alm, sde, or timestamp.')

        if self.config['sde_min_priority'] is not None:
            bad_priority_msg = 'Incorrect sde_min_priority specified in configuration. Valid values are > 0 '
            bad_priority_msg += 'and <= 10'

            try:
                self.config['sde_min_priority'] = int(self.config['sde_min_priority'])
            except:
                raise AlmException(bad_priority_msg)

            if self.config['sde_min_priority'] < 1 or self.config['sde_min_priority'] > 10:
                raise AlmException(bad_priority_msg)
        else:
            self.config['sde_min_priority'] = 1

        if self.config['test_alm'] and self.config['test_alm'] not in AlmConnector.TEST_OPTIONS:
            raise AlmException('Incorrect test_alm configuration setting. '
                               'Valid values are: %s' % ','.join(AlmConnector.TEST_OPTIONS))

        self.config.process_boolean_config('start_fresh')
        self.config.process_boolean_config('show_progress')
        self.config.process_boolean_config('how_tos_in_scope')
        self.config.process_boolean_config('alm_standard_workflow')
        self.config.process_json_dict('alm_custom_fields')

        if self.feature_custom_lookup:
            self.config.process_json_dict('alm_custom_lookup_fields')

        self.init_custom_fields()

        if self.config['start_fresh'] and not self.alm_supports_delete():
            raise AlmException('Incorrect start_fresh configuration: task deletion is not supported.')

        self.alm_plugin.post_conf_init()

        if self.ALM_PRIORITY_MAP in self.config:
            self.config.process_json_str_dict(self.ALM_PRIORITY_MAP)
            if not self.config[self.ALM_PRIORITY_MAP]:
                self.config[self.ALM_PRIORITY_MAP] = self.default_priority_map
            self._validate_alm_priority_map()

        matches = re.findall('\$\{?([a-zA-Z_]+)\}?', self.config['alm_title_format'])
        if not matches:
            raise AlmException('Incorrect alm_title_format configuration')
        if 'title' not in matches:
            raise AlmException('Incorrect alm_title_format configuration. Missing ${title}')
        if 'task_id' not in matches:
            raise AlmException('Incorrect alm_title_format configuration. Missing ${task_id}')
        if 'context' in matches and not self.config['alm_context']:
            raise AlmException('Missing alm_context in configuration')

        for match in matches:
            if match not in AlmConnector.FIELD_OPTIONS:
                raise AlmException('Incorrect alm_title_format configuration. Invalid field: ${%s}' % match)

        logger.info('*** AlmConnector initialized ***')

    def init_custom_fields(self):
        """
        Apply any project-level macro substitutions to the custom field and lookup configuration

        Available macros are:
         - $application - Name of the application
         - $project - Name of the project
         - $context - User-defined context
        """
        mapping = {
            'application': self.config['sde_application'],
            'project': self.config['sde_project'],
            'context': self.config['alm_context']
        }

        config_custom_fields = ['alm_custom_fields']
        if self.feature_custom_lookup:
            config_custom_fields.append('alm_custom_lookup_fields')

        for config_option in config_custom_fields:
            self.transform_config_value(config_option, mapping)

    def _transform_value(self, value, mapping):
        macros = re.findall('\$\{?([a-zA-Z_]+)\}?', value)
        for required_macro in macros:
            if required_macro not in mapping or not mapping[required_macro]:
                raise AlmException("Missing value for configuration macro ${%s}" % required_macro)
        return Template(value).substitute(mapping).strip()

    def transform_config_value(self, key, mapping):
        """
        Perform macro substitutions on configuration
         - key - Configuration key
         - mapping - dictionary of macro->substitution values
        """
        for field, value in self.config[key].iteritems():
            if isinstance(value, list):
                new_value = []
                for list_item in value:
                    new_value.append(self._transform_value(list_item, mapping))
                self.config[key][field] = new_value
            elif isinstance(value, basestring):
                self.config[key][field] = self._transform_value(value, mapping)
            else:
                raise TypeError('Unsupported type, cannot transform value: %s' % value)

    def alm_connect(self):
        self.alm_connect_server()

        if self.config['test_alm'] == 'server':
            return

        self.alm_connect_project()

        if self.config['test_alm'] == 'project':
            return

        self.alm_validate_configurations()

    @abstractmethod
    def alm_connect_server(self):
        """ Sets up a connection to the ALM tool.

        Raises an AlmException on encountering an error
        """
        pass

    def alm_validate_configurations(self):
        """ Validates alm-specific configurations

        Raises an AlmException on encountering an error
        """
        pass

    @abstractmethod
    def alm_connect_project(self):
        """ Sets up a connection to the ALM tool.

        Raises an AlmException on encountering an error
        """
        pass

    @abstractmethod
    def alm_get_task(self, task):
        """ Returns an AlmTask that represents the value of this
        SD Elements task in the ALM, or None if the task doesn't exist

        Raises an AlmException on encountering an error

        Keyword arguments:
        task  -- An SDE task
        """
        pass

    @abstractmethod
    def alm_add_task(self, task):
        """ Adds SD Elements task to the ALM tool.

        Returns a string representing the task in the ALM tool,
        or None if that's not possible. This string will be
        added to a note for the task.

        Raises an AlmException on encountering an error.

        Keyword arguments:
        task  -- An SDE task
        """
        pass

    def alm_supports_delete(self):
        """ Returns True if Task Delete is supported by the ALM
        """
        delete_method = getattr(self, "alm_remove_task", None)
        if delete_method:
            return callable(delete_method)
        return False

    @abstractmethod
    def alm_update_task_status(self, task, status):
        """ Updates the specified task in the ALM tool with a new status

        Raises an AlmException on encountering an error

        Keyword arguments:
        task  -- An AlmTask representing the task to be updated
        status -- A string specifying the new status. Either 'DONE', 'TODO',
                  or 'NA'
        """
        pass

    @abstractmethod
    def alm_disconnect(self):
        """ Attempt to disconnect from ALM, if necessary

        Raises an AlmException on encountering an error
        """
        pass

    def sde_connect(self):
        """ Connects to SD Elements server specified in plugin object

        Raises an AlmException on encountering an error
        """
        if not self.sde_plugin:
            raise AlmException('Requires initialization')
        try:
            self.sde_plugin.connect()
        except APIError, err:
            raise AlmException('Unable to connect to SD Elements. Please review URL, id,'
                    ' and password in configuration file. Reason: %s' % (str(err)))

        self.sde_validate_configuration()

    def sde_validate_configuration(self):
        """ Validate selected phases, if applicable """
        if not self.config['selected_tasks']:
            result = self.sde_plugin.get_phases()
            if not result:
                raise AlmException('Unable to retrieve phases from SD Elements')

            all_phases_slugs = [phase['slug'] for phase in result['phases']]
            for selected_phase in self.config['alm_phases']:
                if selected_phase not in all_phases_slugs:
                    raise AlmException('Incorrect alm_phase configuration: %s is not a valid phase' % selected_phase)

    def is_sde_connected(self):
        """ Returns true if currently connected to SD Elements"""
        if not self.sde_plugin:
            return False
        return self.sde_plugin.connected

    def _validate_alm_priority_map(self):
        """
        Validate a priority mapping dictionary. The mapping specifies which value to use in another system
        based on the SD Elements task's priority numeric value. Priorities are numeric values from the range 1 to 10.

        This method ensures that:

         1. Keys represent a single priority {'10':'Critical'} or a range of priorities {'7-10':'High'}
         2. Priorities 1 to 10 are represented exactly once in the dictionary keys
         3. Mappings containing a range of priorities {'7-10':'High'} must have their values ordered from low to high.

        Valid example:
        {'1-3': 'Low', '4-6': 'Medium', '7-10': 'High'}

        All SD Elements tasks with priority 1 to 3 are to be mapped to the value "Low" in the other system.
        All SD Elements tasks with priority 4 to 6 are to be mapped to the value "Medium" in the other system.
        All SD Elements tasks with priority 7 to 10 are to be mapped to the value "High" in the other system.

        Invalid examples:
        {'1-3': 'Low', '4-6': 'Medium', '7-9': 'High'}
        {'1-3': 'Low', '4-6': 'Medium', '6-10': 'High'}
        {'3-1': 'Low', '6-4': 'Medium', '10-7': 'High'}
        """
        if self.ALM_PRIORITY_MAP not in self.config:
            return

        priority_set = set()
        for key, value in self.config[self.ALM_PRIORITY_MAP].iteritems():
            if not RE_MAP_RANGE_KEY.match(key):
                raise AlmException('Unable to process %s (not a JSON dictionary). '
                        'Reason: Invalid range key %s' % (self.ALM_PRIORITY_MAP, key))

            if '-' in key:
                lrange, hrange = key.split('-')
                lrange = int(lrange)
                hrange = int(hrange)
                if lrange >= hrange:
                    raise AlmException('Invalid %s entry %s => %s: Priority %d should be less than %d' %
                                       (self.ALM_PRIORITY_MAP, key, value, lrange, hrange))
                for mapped_priority in range(lrange, hrange+1):
                    if mapped_priority in priority_set:
                        raise AlmException('Invalid %s entry %s => %s: Priority %d is duplicated' %
                                          (self.ALM_PRIORITY_MAP, key, value, mapped_priority))
                    priority_set.add(mapped_priority)
            else:
                key_value = int(key)
                if key_value in priority_set:
                    raise AlmException('Invalid %s entry %s => %s: Priority %d is duplicated' %
                                      (self.ALM_PRIORITY_MAP, key, value, key_value))
                priority_set.add(key_value)

        for mapped_priority in xrange(1, 11):
            if mapped_priority not in priority_set:
                raise AlmException('Invalid %s: missing a value mapping for priority %d' %
                                   (self.ALM_PRIORITY_MAP, mapped_priority))

    @staticmethod
    def _extract_task_id(full_task_id):
        """
        Extract the task id e.g. "CT213" from the full project_id-task_id string e.g. "123-CT213"
        """
        task_id = None
        task_search = re.search('^(\d+)-([^\d]+\d+)$', full_task_id)
        if task_search:
            task_id = task_search.group(2)
        return task_id

    @staticmethod
    def get_alm_task_title(config, task, fixed=False):
        """
        Return the user-defined formatted fixed or full alm title for an SDE task. The fixed title can be used
        to uniquely identify an issue inside the ALM, allowing one ALM project to sync
        with more than one instance of the same SDE task
        """
        task_id = AlmConnector._extract_task_id(task['id'])

        # Remove the task id from the title to get the actual title
        title = re.sub('^%s:\s+' % task_id, '', task['title'])

        mapping = {
            'task_id': '%s:' % task_id,  # Force a suffix to avoid finding "T222" when searching with "T2"
            'context': config['alm_context'],
            'application': config['sde_application'],
            'project': config['sde_project'],
            'title': title,
        }
        if fixed:
            mapping['title'] = ''

        return Template(config['alm_title_format']).substitute(mapping).strip()

    def sde_get_tasks(self):
        """ Gets all tasks for project in SD Elements

        Raises an AlmException on encountering an error
        """

        if not self.sde_plugin:
            raise AlmException('Requires initialization')

        try:
            if self.config['selected_tasks']:
                return self.sde_plugin.get_task_list()
            else:
                return self.sde_plugin.get_task_list(priority__gte=self.config['sde_min_priority'])
        except APIError, err:
            logger.error(err)
            raise AlmException('Unable to get tasks from SD Elements. Please ensure'
                    ' the application and project are valid and that the user has'
                    ' sufficient permission to access the project. Reason: %s' % (str(err)))

    def sde_get_task(self, task_id):
        """ Returns a single task from SD Elements w given task_id

        Raises an AlmException if task doesn't exist or any other error
        """
        if not self.sde_plugin:
            raise AlmException('Requires initialization')

        try:
            return self.sde_plugin.api.get_task(task_id)
        except APIError, err:
            logger.error(err)
            raise AlmException('Unable to get task in SD Elements. Reason: %s' % (str(err)))

    def _add_note(self, task_id, note_msg, filename, status):
        """ Convenience method to add note """
        if not self.sde_plugin:
            raise AlmException('Requires initialization')

        try:
            self.sde_plugin.api.add_task_ide_note(task_id, note_msg, filename, status)
            logger.debug('Successfully set note for task %s' % task_id)

        except APIError, err:
            logger.error(err)
            raise AlmException('Unable to add note in SD Elements. Reason: %s' % (str(err)))

    def in_scope(self, task):
        """ Check to see if an SDE task is in scope

        For example, has one of the appropriate phases
        """
        tid = self._extract_task_id(task['id'])
        if self.config['selected_tasks']:
            return tid in self.config['selected_tasks']

        in_scope = (task['phase'] in self.config['alm_phases'] and
                    task['priority'] >= self.config['sde_min_priority'])

        if in_scope and self.config['sde_tags_filter']:
            in_scope = in_scope and set(self.config['sde_tags_filter']).issubset(task['tags'])

        if in_scope and self.config['sde_verification_filter']:
            # Translate null to 'none' to match filter options
            if not task['verification_status']:
                task['verification_status'] = 'none'
            in_scope = in_scope and task['verification_status'] in self.config['sde_verification_filter']

        return in_scope

    def sde_update_task_status(self, task, status):
        """ Updates the status of the given task in SD Elements

        Raises an AlmException on encountering an error

        Keyword arguments:
        task  -- An SD Elements task representing the task to be updated
        status -- A string specifying the new status. Either 'DONE', 'TODO',
                  or 'NA'
        """
        if not self.sde_plugin:
            raise AlmException('Requires initialization')

        logger.debug('Attempting to update task %s to %s' % (task['id'], status))

        try:
            self.sde_plugin.api.update_task_status(task['id'], status)
        except APIError, err:
            logger.error(err)
            raise AlmException('Unable to update the task status in SD '
                               'Elements. Either the task no longer '
                               'exists, there was a problem connecting '
                               'to the server, or the status was invalid')
        logger.info('Status for task %s successfully set in SD Elements' % task['id'])

        note_msg = 'Task status changed to %s via %s' % (status, self.alm_name)
        try:
            self._add_note(task['id'], note_msg, '', status)
        except APIError, err:
            logger.error('Unable to set a note to mark status '
                         'for %s to %s. Reason: %s' % (task['id'], status, str(err)))

    def convert_markdown_to_alm(self, content, ref):
        return content

    def sde_get_task_content(self, task):
        """ Convenience method that returns the text that should go into
        content of an ALM ticket/defect/story for a given task.

        Raises an AlmException on encountering an error

        Keyword arguments:
        task  -- An SD Elements task representing the task to enter in the
                 ALM
        """
        content = '%s\n\nImported from SD Elements: [%s](%s)' % (task['content'], task['url'], task['url'])
        if self.config['how_tos_in_scope'] and task['implementations']:
            content += '\n\n# How Tos:\n\n'
            for implementation in task['implementations']:
                content += '## %s\n\n' % (implementation['title'])
                content += implementation['content'] + '\n\n'

        content = RE_CODE_DOWNLOAD.sub(r'https://%s/\1' % self.config['sde_server'], content)

        return self.convert_markdown_to_alm(content, ref=task['id'])

    def output_progress(self, percent):
        if self.config['show_progress']:
            print str(percent)+"% complete"
            sys.stdout.flush()

    def status_match(self, alm_status, sde_status):
        if sde_status == "NA" or sde_status == "DONE":
            return alm_status == "DONE"
        else:
            return alm_status == "TODO"

    def filter_tasks(self, tasks):
        tasks = [AlmConnector.add_alm_title(self.config, task) for task in tasks if self.in_scope(task)]

        return tasks

    @staticmethod
    def add_alm_title(config, task):
        task['alm_full_title'] = AlmConnector.get_alm_task_title(config, task, fixed=False)
        task['alm_fixed_title'] = AlmConnector.get_alm_task_title(config, task, fixed=True)
        return task

    def synchronize(self):
        """ Synchronizes SDE project with ALM project.

        Reviews every task in the SDE project:
        - if the task exists in both SDE & ALM and the status is the same
          in both, nothing happens
        - if the task exists in both SDE & ALM and the status differs, then
          the conflict policy takes effect. Either the newest status based on
          timestamp is used, or the SDE status is used in every case, or
          the ALM tool status is used in every case. Default is ALM tool
          status
        - if the task only exists in SDE, the task is added to the ALM
          tool
        - NOTE: if a task that was previously imported from SDE into the
          ALM is later removed in the same SDE project, then the task is
          effectively orphaned. The task must be removed manually from the
          ALM tool

        Raises an AlmException on encountering an error
        """
        try:
            if not self.sde_plugin:
                raise AlmException('Requires initialization')

            if self.config['test_alm']:
                self.alm_connect()
                return

            # Attempt to connect to SDE & ALM
            progress = 0

            self.sde_connect()
            progress += 2
            self.output_progress(progress)

            self.alm_connect()
            progress += 2
            self.output_progress(progress)

            # Attempt to get all tasks
            tasks = self.sde_get_tasks()
            logger.info('Retrieved all tasks from SDE')

            # Filter tasks - progress must match reality
            tasks = self.filter_tasks(tasks)

            logger.info('Filtered tasks')

            if self.config['start_fresh']:
                total_work = progress + len(tasks) * 2
            else:
                total_work = progress + len(tasks)

            if self.config['start_fresh']:
                for task in tasks:
                    alm_task = self.alm_get_task(task)
                    if alm_task:
                        self.alm_remove_task(alm_task)
                    progress += 1
                    self.output_progress(100*progress/total_work)

            for task in tasks:
                tid = self._extract_task_id(task['id'])
                progress += 1
                self.output_progress(100*progress/total_work)

                alm_task = self.alm_get_task(task)
                if alm_task:
                    if not self.config['alm_standard_workflow']:
                        continue

                    # Exists in both SDE & ALM
                    if not self.status_match(alm_task.get_status(), task['status']):
                        # What takes precedence in case of a conflict of
                        # status. Start with ALM
                        precedence = 'alm'
                        updated_system = 'SD Elements'

                        if self.config['conflict_policy'] == 'sde':
                            precedence = 'sde'
                        elif self.config['conflict_policy'] == 'timestamp':
                            sde_time = datetime.fromtimestamp(task['timestamp'])
                            alm_time = alm_task.get_timestamp()
                            logger.debug('Comparing timestamps for task %s - SDE: %s, ALM: %s' %
                                          (task['id'], str(sde_time), str(alm_time)))
                            if sde_time > alm_time:
                                precedence = 'sde'

                        status = alm_task.get_status()
                        if precedence == 'alm':
                            self.sde_update_task_status(task, alm_task.get_status())
                        else:
                            self.alm_update_task_status(alm_task, task['status'])
                            status = task['status']
                            updated_system = self.alm_name
                        self.emit.info('Updated status of task %s in %s to %s' % (tid, updated_system, status))
                else:
                    # Only exists in SD Elements
                    # Skip if this task should not be added to ALM
                    if ((not self.config['selected_tasks'] and task['status'] not in self.config['sde_statuses_in_scope']) or
                            task['id'] in self.ignored_tasks):
                        continue
                    ref = self.alm_add_task(task)
                    self.emit.info('Added task %s to %s' % (tid, self.alm_name))
                    note_msg = 'Task synchronized in %s. Reference: %s' % (self.alm_name, ref)
                    self._add_note(task['id'], note_msg, '', task['status'])
                    logger.debug(note_msg)

            logger.info('Synchronization complete')

            self.alm_disconnect()

        except AlmException:
            self.alm_disconnect()
            raise

    def translate_priority(self, priority):
        """ Translates an SDE priority into a GitHub label """
        pmap = self.config[self.ALM_PRIORITY_MAP]

        if not pmap:
            return None

        try:
            priority = int(priority)
        except TypeError:
            logger.error('Could not coerce %s into an integer' % priority)
            raise AlmException("Error in translating SDE priority to %s: "
                               "%s is not an integer priority" % (priority, self.alm_name))

        for key in pmap:
            if '-' in key:
                lrange, hrange = key.split('-')
                lrange = int(lrange)
                hrange = int(hrange)
                if lrange <= priority <= hrange:
                    return pmap[key]
            else:
                if int(key) == priority:
                    return pmap[key]
