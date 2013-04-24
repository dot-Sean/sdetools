from datetime import datetime
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
RE_TASK_IDS = re.compile('^C?T\d+$')

class AlmException(Error):
    """ Class for ALM Exceptions """

    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)

class AlmTask(object):
    """
    Abstract base class to represent a task in an ALM. This should be subclassed 
    by an implementation for a specific ALM that can translate the ALM fields to 
    SDE fields. For example, the ALM might use 'severity' while SD Elements uses 
    'priority'
    """

    @abstractmethod
    def get_task_id(self):
        """ Returns an ID string compatiable with SD Elements """
        pass

    @abstractmethod
    def get_priority(self):
        """ Returns a priority string compatible with SD Elements """
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

    #This is an abstract base class
    __metaclass__ = abc.ABCMeta

    def __init__(self, config, alm_plugin):
        """  Initialization of the Connector

        Keyword arguments:
        sde_plugin -- An SD Elements Plugin configuration object
        alm_plugin -- A plugin to connect to the ALM tool
        """
        self.config = config
        self.sde_plugin = PlugInExperience(self.config)
        self.alm_plugin = alm_plugin
        self._add_alm_config_options()
        self.emit = self.config.emit

    def _add_alm_config_options(self):
        """ Adds ALM config options to the config file"""
        self.config.add_custom_option('alm_phases', 'Phases of the ALM',
                default='requirements,architecture-design,development')
        self.config.add_custom_option('sde_statuses_in_scope', 'SDE statuses that are in scope', 
                default='DONE,TODO,NA')
        self.config.add_custom_option('sde_min_priority', 'Minimum SDE priority in scope',
                default='7')
        self.config.add_custom_option('how_tos_in_scope', 'Whether or not HowTos should be included',
                default='False')
        self.config.add_custom_option('selected_tasks', 'Optionally limit the sync to certain tasks'
                ' (comma seperated, e.g. T12,T13). Note: Overrides other selections.',
                default='')
        self.config.add_custom_option('alm_project', 'Project in ALM Tool',
                default=None)
        self.config.add_custom_option('conflict_policy', 'Conflict policy to use',
                default='alm')
        self.config.add_custom_option('show_progress', 'Show progress',
                default='False')
        self.config.add_custom_option('test_alm_connection', 'Test Alm Connection Only',
                default='False')
        self.config.add_custom_option('alm_standard_workflow', 'Standard workflow in ALM?',
                default='True')
        self.config.add_custom_option('alm_custom_fields', 
                'Customized fields to include when creating a task in ALM '
                '(JSON encoded dictionary of strings)',
                default='')

    def initialize(self):
        """
        Verify that the configuration options are set properly
        """

        #Note: This will consider space as empty due to strip
        #We do this before checking if the config is non-empty later
        self.config['selected_tasks'] = [x.strip(' ') 
            for x in self.config['selected_tasks'].split(',') if x.strip(' ')]
        for task in self.config['selected_tasks']:
            if not RE_TASK_IDS.match(task):
                raise UsageError('Invalid Task ID: %s' % (task))

        if not self.config['selected_tasks']:
            if not self.config['alm_phases']:
                raise AlmException('Missing alm_phases in configuration')

            self.config['alm_phases'] = self.config['alm_phases'].split(',')

            if not self.config['sde_statuses_in_scope']:
                raise AlmException('Missing the SD Elements statuses in scope')

            self.config['sde_statuses_in_scope'] = self.config['sde_statuses_in_scope'].split(',')
            for status in self.config['sde_statuses_in_scope']:
                if status not in('TODO', 'DONE', 'NA'):
                    raise AlmException('Invalid status specified in '
                                   'sde_statuses_in_scope')

        if (not self.config['conflict_policy'] or
            not (self.config['conflict_policy'] == 'alm' or
                 self.config['conflict_policy'] == 'sde' or
                 self.config['conflict_policy'] == 'timestamp')):
            raise AlmException('Missing or incorrect conflict_policy '
                               'in configuration. Valid values are '
                               'alm, sde, or timestamp.')

        if (self.config['sde_min_priority']):
            bad_priority_msg =  'Incorrect sde_min_priority specified in configuration. Valid values are > 0 '
            bad_priority_msg += ' and <= 10'

            try:
                self.config['sde_min_priority'] = int(self.config['sde_min_priority'])
            except:
                raise AlmException(bad_priority_msg)

            if (self.config['sde_min_priority'] < 1 or self.config['sde_min_priority'] >10):
                raise AlmException(bad_priority_msg)
        else:
            self.config['sde_min_priority'] = 1

        self.config.process_boolean_config('show_progress')
        self.config.process_boolean_config('how_tos_in_scope')
        self.config.process_boolean_config('test_alm_connection')
        self.config.process_boolean_config('alm_standard_workflow')
        self.config.process_json_str_dict('alm_custom_fields')

        logger.info('*** AlmConnector initialized ***')

    @abstractmethod
    def alm_connect(self):
        """ Sets up a connection to the ALM tool.

        Raises an AlmException on encountering an error
        """
        pass

    @abstractmethod
    def alm_get_task(self, task):
        """ Returns an AlmTask that represents the value of this
        SD Elemets task in the ALM, or None if the task doesn't exist

        Raises an AlmException on encountering an error

        Keyword arguments:
        task  -- An SDE task
        """
        pass

    @abstractmethod
    def alm_add_task(self, task):
        """ Adds SD Elements task to the ALM tool.

        Returns a string represeting the task in the ALM tool,
        or None if that's not possible. This string will be
        added to a note for the task.

        Raises an AlmException on encountering an error.

        Keyword arguments:
        task  -- An SDE task
        """
        pass

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

    def is_sde_connected(self):
        """ Returns true if currently connected to SD Elements"""
        if not self.sde_plugin:
            return False
        return self.sde_plugin.connected

    def sde_get_tasks(self):
        """ Gets all tasks for project in SD Elements

        Raises an AlmException on encountering an error
        """

        if not self.sde_plugin:
            raise AlmException('Requires initialization')

        try:
            return self.sde_plugin.get_task_list()
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
            self.sde_plugin.api.add_task_ide_note(task_id, note_msg,
                                             filename, status)
            logger.debug('Successfuly set note for task %s' % task_id)

        except APIError, err:
            logger.error(err)
            raise AlmException('Unable to add note in SD Elements. Reason: %s' % (str(err)))

    def in_scope(self, task):
        """ Check to see if an SDE task is in scope

        For example, has one of the appropriate phases
        """
        tid = task['id'].split('-', 1)[-1]
        if self.config['selected_tasks']:
            return (tid in self.config['selected_tasks'])
        return (task['phase'] in self.config['alm_phases'] and
            task['status'] in self.config['sde_statuses_in_scope'] and
            task['priority'] >= self.config['sde_min_priority'])

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

        note_msg = 'Task status changed via %s' % self.alm_name
        try:
            self._add_note(task['id'], note_msg, '', status)
        except APIError, err:
            logger.error('Unable to set a note to mark status '
                         'for %s to %s' % (task['id'], status))

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
        if sde_status=="NA" or sde_status=="DONE":
            return alm_status == "DONE"
        else:
            return alm_status == "TODO"

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

            if self.config['test_alm_connection']:
                self.alm_connect()
                return

            #Attempt to connect to SDE & ALM
            progress = 0

            self.sde_connect()
            progress += 2
            self.output_progress(progress)

            self.alm_connect()
            progress += 2
            self.output_progress(progress)

            #Attempt to get all tasks
            tasks = self.sde_get_tasks()
            logger.info('Retrieved all tasks from SDE')

            #Prune unnecessary tasks - progress must match reality
            tasks = [task for task in tasks if self.in_scope(task)]

            logger.info('Pruned tasks out of scope')

            total_work = (progress+len(tasks))

            for task in tasks:
                tid = task['id'].split('-', 1)[-1]
                progress += 1
                self.output_progress(100*progress/total_work)

                alm_task = self.alm_get_task(task)
                if alm_task:
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
                            logger.debug('comparing timestamps for task %s - SDE: %s, ALM: %s' %
                                          (task['id'], str(sde_time), str(alm_time)))
                            if (sde_time > alm_time):
                                precedence = 'sde'

                        status = alm_task.get_status()
                        if (precedence == 'alm'):
                            self.sde_update_task_status(task, alm_task.get_status())
                        else:
                            self.alm_update_task_status(alm_task, task['status'])
                            status = task['status']
                            updated_system = self.alm_name
                        self.emit.info('Updated status of task %s in %s to %s' % (tid, updated_system, status))
                else:
                    #Only exists in SD Elements, add it to ALM
                    ref = self.alm_add_task(task)
                    self.emit.info('Added task %s to %s' % (tid, self.alm_name))
                    note_msg = 'Task synchronized in %s. Reference: %s' % (self.alm_name, ref)
                    self._add_note(task['id'], note_msg, '', task['status'])
                    logger.debug(note_msg)

            logger.info('Synchronization complete')
            self.alm_disconnect()

        except AlmException, err:
            self.alm_disconnect()
            raise err

