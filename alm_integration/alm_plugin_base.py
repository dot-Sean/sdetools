from abc import ABCMeta, abstractmethod
from datetime import datetime

from sdelib.restclient import APIError
from sdelib.interactive_plugin import PlugInExperience

from sdelib import log_mgr
logger = log_mgr.mods.add_mod(__name__)

class AlmException(Exception):
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

    #This is an abstract base class
    __metaclass__ = ABCMeta

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

    def _add_alm_config_options(self):
        """ Adds ALM config options to the config file"""
        self.config.add_custom_option('alm_phases', 'Phases of the ALM')
        self.config.add_custom_option('sde_statuses_in_scope', 'SDE statuses that are in scope')
        self.config.add_custom_option('sde_min_priority', 'Minimum SDE priority in scope')
        self.config.add_custom_option('how_tos_in_scope', 'Whether or not HowTos should be included')
        self.config.add_custom_option('alm_project', 'Project in ALM Tool')
        self.config.add_custom_option('conflict_policy', 'Conflict policy to use')

    def initialize(self):
        #Verify that the configuration options are set properly
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

        logger.info('*** AlmConnector initialized ***')

    @abstractmethod
    def alm_name(self):
        """ Returns a string representation of the ALM, e.g. 'JIRA' """
        pass

    @abstractmethod
    def alm_connect(self):
        """ Sets up a connection to the ALM tool.

        Raises an AlmException on encountering an error
        """
        pass

    @abstractmethod
    def alm_get_task (self, task):
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
        except APIError:
            raise AlmException('Unable to connect to SD Elements. ' +
                           'Please review URL, id, and password in ' +
                           'configuration file.')

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
            raise AlmException('Unable to get tasks from SD Elements. '
                               'Please ensure the application and project '
                               'are valid and that the user has sufficient '
                               'permission to access the project')

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
            raise AlmException('Unable to get task in SD Elements')

    def _add_note(self, task_id, note_msg, filename, status):
        """ Convenience method to add note """
        if not self.sde_plugin:
            raise AlmException('Requires initialization')

        try:
            self.sde_plugin.api.add_note(task_id, note_msg,
                                             filename, status)
            logger.debug('Successfuly set note for task %s' % task_id)

        except APIError, err:
            logger.error(err)
            raise AlmException('Unable to add note in SD Elements')

    def in_scope(self, task):
        """ Check to see if an SDE task is in scope

        For example, has one of the appropriate phases
        """
        return (task['phase'] in self.config['alm_phases']  and
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
            logger.error('Incorrect initialization')
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

        note_msg = 'Task status changed via %s' % self.alm_name()
        try:
            self._add_note(task['id'], note_msg, '', status)
        except APIError, err:
            logger.info('Unable to set a note to mark status '
                         'for %s to %s' % (task['id'], status))

    def sde_get_task_content(self, task):
        """ Convenience method that returns the text that should go into
        contents of an ALM ticket/defect/story for a given task.

        Raises an AlmException on encountering an error

        Keyword arguments:
        task  -- An SD Elements task representing the task to enter in the
                 ALM
        """
        contents = '%s\n\nImported from SD Elements: %s' % (task['content'], task['url'])
        if self.config['how_tos_in_scope'] == 'True':
            if task['implementations']:
                contents = contents + '\n\nHow Tos:\n\n'
                for implementation in task['implementations']:
                    contents = contents + implementation['title'] + '\n\n'
                    contents = contents + implementation['content'] + '\n\n'
        return contents

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

            #Attempt to connect to SDE & ALM
            self.sde_connect()
            self.alm_connect()

            #Attempt to get all tasks
            tasks = self.sde_get_tasks()
            logger.info('Retrieved all tasks from SDE')

            for task in tasks:
                if not self.in_scope(task):
                    continue
                alm_task = self.alm_get_task(task)
                if alm_task:
                    #Exists in both SDE & ALM
                    if alm_task.get_status() != task['status']:
                        # What takes precedence in case of a conflict of
                        # status. Start with ALM
                        precedence = 'alm'
                        if self.config['conflict_policy'] == 'sde':
                            precedence = 'sde'
                        elif self.config['conflict_policy'] == 'timestamp':
                            sde_time = datetime.fromtimestamp(task['timestamp'])
                            alm_time = alm_task.get_timestamp()
                            logger.debug('comparing timestamps for task %s - SDE: %s, ALM: %s' %
                                          (task['id'], str(sde_time), str(alm_time)))
                            if (sde_time > alm_time):
                                precedence = 'sde'
                        if (precedence == 'alm'):
                            self.sde_update_task_status(task, alm_task.get_status())
                        else:
                            self.alm_update_task_status(alm_task, task['status'])
                        logger.debug('Updated status of task %s in %s' % (task['id'], precedence))
                else:
                    #Only exists in SD Elements, add it to ALM
                    ref = self.alm_add_task(task)
                    note_msg = 'Task synchronized in %s' % self.alm_name()
                    if ref:
                        note_msg += '. Reference: %s' % (ref)
                    self._add_note(task['id'], note_msg, '', task['status'])

            logger.info('Synchronization complete')
            self.alm_disconnect()

        except AlmException, err:
            self.alm_disconnect()
            raise err

