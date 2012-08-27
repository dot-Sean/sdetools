import sys, os
sys.path.append(os.path.split(os.path.split(os.path.abspath(__file__))[0])[0])

import csv

from sdelib.apiclient import APIError
from sdelib.conf_mgr import config
from sdelib.commons import show_error, json
from sdelib.interactive_plugin import PlugInExperience
from abc import ABCMeta, abstractmethod
from datetime import datetime
import logging
import csv

class AlmException(Exception):
     """ Class for ALM Exceptions """

     def __init__(self, value):
          self.value = value

     def __str__(self):
          return repr(self.value)

class AlmTask:
     """
          Abstract base class to represent a task in an ALM. This should be
          subclassed by an implementation for a specific ALM that can
          translate the ALM fields to SDE fields. For example, the ALM
          might use 'severity' while SD Elements uses 'priority'
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

class AlmConnector:
     """
          Abstract base class for connectors to Application Lifecycle
          Management tools such as JIRA, Team Foundation Server, Rally, etc.
     """

     #This is an abstract base class
     __metaclass__ = ABCMeta

     #ALM Configuration
     configuration = None

     def __init__(self, sde_plugin, alm_plugin):
          """  Initialization of the Connector

          Keyword arguments:
          sde_plugin  -- An SD Elements Plugin configuration object
          alm_plugin -- A plugin to connect to the ALM tool
          """
          logging.basicConfig(format='%(asctime)s,%(levelname)s:%(message)s',
                              filename='info.log', level=logging.DEBUG)
          self.sde_plugin = sde_plugin
          self.alm_plugin = alm_plugin

          #Verify that the configuration options are set properly
          if not self.sde_plugin.config['alm_phases']:
                 raise AlmException('Missing alm_phases in configuration')
          else:
               self.sde_plugin.config['alm_phases'] = self.sde_plugin.config['alm_phases'].split(',')

          if not self.sde_plugin.config['sde_statuses_in_scope']:
                 raise AlmException('Missing the SD Elements statuses in scope')
          else:
               self.sde_plugin.config['sde_statuses_in_scope'] = self.sde_plugin.config['sde_statuses_in_scope'].split(',')
               for status in self.sde_plugin.config['sde_statuses_in_scope']:
                    if status not in('TODO','DONE','NA'):
                         raise AlmException('Invalid status specified in '
                                            'sde_statuses_in_scope')

          if (not self.sde_plugin.config['conflict_policy'] or
              not (self.sde_plugin.config['conflict_policy'] == 'alm' or
                   self.sde_plugin.config['conflict_policy'] == 'sde' or
                   self.sde_plugin.config['conflict_policy'] == 'timestamp')):
               raise AlmException('Missing or incorrect conflict_policy '
                                  'in configuration. Valid values are '
                                  'alm, sde, or timestamp.')

          logging.info('---------')
          logging.info('---------')
          logging.info('AlmConnector initialized')

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
          except APIError as err:
               raise AlmException('Unable to connect to SD Elements.' +
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
          except APIError as err:
               logging.error(err)
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
          except APIError as err:
               logging.error(err)
               raise AlmException('Unable to get task in SD Elements')

     def _add_note(self, task_id, note_msg, filename, status):
          """ Convenience method to add note """
          if not self.sde_plugin:
               raise AlmException('Requires initialization')

          try:
               self.sde_plugin.api.add_note(task_id, note_msg,
                                                filename, status)
               logging.debug('Sucessfuly set note for task %s' % task_id)

          except APIError as err:
               logging.error(err)
               raise AlmException('Unable to add note in SD Elements')

     def in_scope(self, task):
          """ Check to see if an SDE task is in scope

          For example, has one of the appropriate phases
          """
          return (task['phase'] in self.sde_plugin.config['alm_phases']  and
                  task['status'] in self.sde_plugin.config['sde_statuses_in_scope'])

     def sde_update_task_status(self, task, status):
          """ Updates the status of the given task in SD Elements

          Raises an AlmException on encountering an error

          Keyword arguments:
          task  -- An SD Elements task representing the task to be updated
          status -- A string specifying the new status. Either 'DONE', 'TODO',
                    or 'NA'
          """
          if not self.sde_plugin:
               logging.error('Incorrect initialization')
               raise AlmException('Requires initialization')

          logging.debug('Attempting to update task %s to %s' % (task['id'], status))

          try:
               self.sde_plugin.api.update_task_status(task['id'], status)
          except APIError as err:
               logging.error(err)
               raise AlmException('Unable to update the task status in SD '
                                  'Elements. Either the task no longer '
                                  'exists, there was a problem connecting '
                                  'to the server, or the status was invalid')
          logging.info('Status for task %s successfully set in SD Elements' % task['id'])

          note_msg = 'Task status changed via %s' % self.alm_name()
          try:
               self._add_note(task['id'], note_msg, '', status)
          except APIError as err:
               logging.info('Unable to set a note to mark status '
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
          if self.sde_plugin.config['how_tos_in_scope'] == 'True':
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
               logging.info('Retrieved all tasks from SDE')

               for task in tasks:
                    if not self.in_scope(task):
                         continue
                    alm_task = self.alm_get_task(task)
                    if (alm_task):
                         #Exists in both SDE & ALM
                         if alm_task.get_status() != task['status']:
                              #what takes precedence in case of a
                              #conflict of status. Start with ALM
                              precedence = 'alm'
                              if self.sde_plugin.config['conflict_policy'] == 'sde':
                                  precedence = 'sde'
                              elif self.sde_plugin.config['conflict_policy'] == 'timestamp':
                                   sde_time = datetime.fromtimestamp(task['timestamp'])
                                   alm_time = alm_task.get_timestamp()
                                   logging.debug('comparing timestamps for '+
                                                 'task %s - SDE: %s, ALM: %s' %
                                                 (task['id'], str(sde_time),
                                                 str(alm_time)))
                                   if (sde_time > alm_time):
                                        precedence = 'sde'
                              if (precedence == 'alm'):
                                   self.sde_update_task_status(task,
                                   alm_task.get_status())
                              else:
                                   self.alm_update_task_status(alm_task,
                                                              task['status'])
                              logging.debug('Updated status of task ' +
                                               ' %s in %s'
                                               % (task['id'],precedence))
                    else:
                         #Only exists in SD Elements, add it to ALM
                         ref = self.alm_add_task(task)
                         note_msg = 'Task synchronized in %s' % self.alm_name()
                         if (ref):
                              note_msg += '. Reference: %s' % (ref)
                         self._add_note(task['id'], note_msg, '', task['status'])

               logging.info('Synchronization complete')
               self.alm_disconnect()

          except AlmException as err:
               self.alm_disconnect()
               raise err

def add_alm_config_options(config):
     """ Adds ALM config options to the config file"""
     config.add_custom_option('alm_phases',
                             'Phases of the ALM',
                             '-alm_phases')
     config.add_custom_option('sde_statuses_in_scope',
                             'SDE statuses that are in scope',
                             '-sde_statuses_in_scope')
     #how_tos_in_scope
     config.add_custom_option('how_tos_in_scope',
                             'Whether or not HowTos should be included',
                             '-how_tos_in_scope')
     config.add_custom_option('alm_method',
                             'HTTP or HTTPS for ALM server',
                             '-alm_method',
                             default='https')
     config.add_custom_option('alm_server',
                             'Server of the ALM',
                             '-alm_server')
     config.add_custom_option('alm_id',
                             'Username for ALM Tool',
                             '-alm_id')
     config.add_custom_option('alm_password',
                             'Password for ALM Tool',
                             '-alm_password')
     config.add_custom_option('alm_project',
                             'Project in ALM Tool',
                             '-alm_project')
     config.add_custom_option('conflict_policy',
                             'Conflict policy to use',
                             '-conflict_policy')



