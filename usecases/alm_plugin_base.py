#!/usr/bin/python
#
# Version 0.01
# Rohit Sethi
# Copyright SDElements Inc
#
# Proof of concept for extensible two way
# integration with ALM tools

import sys, os
sys.path.append(os.path.split(os.path.split(os.path.abspath(__file__))[0])[0])

import csv

from sdelib.conf_mgr import config
from sdelib.commons import show_error, json
from sdelib.interactive_plugin import PlugInExperience
from abc import ABCMeta, abstractmethod
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
          """ Returns a timestamp compatible with SD Elements """
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

     #Conflict policy. ALM tool takes precedence by default
     conflict_policy = 'ALM'

     def __init__(self, sde_plugin, alm_plugin , configuration):
          """  Initialization of the Connector

          Keyword arguments:
          sde_plugin  -- An SD Elements Plugin configuration object
          configuration -- A configuration object specific to this ALM

          """
          logging.basicConfig(format='%(asctime)s,%(levelname)s:%(message)s'
                              ,filename='info.log',level=logging.INFO)
          self.sde_plugin = sde_plugin
          self.alm_plugin = alm_plugin
          self.configuration = configuration
          logging.info("---------")
          logging.info("---------")
          logging.info("AlmConnector initialized")

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

          Raises an AlmException on encountering an error

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
          status -- A string specifying the new status. Either 'Done', 'TODO',
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
          if (self.sde_plugin == None):         
               raise AlmException("Requires initialization")
          
          retval = self.sde_plugin.connect()
          
          if (retval[0]):
               raise AlmException("Unable to connect to SD Elements." +
                              "Please review URL, id, and password in " +
                              "configuration file.")
          


     def sde_get_tasks(self):
          """ Gets all tasks for project in SD Elements

          Raises an AlmException on encountering an error

          """
          
          if (self.sde_plugin == None):            
               raise AlmException("Requires initialization")

          #Filter by phases if configured if (configuration['phases']):
          
          retval = self.sde_plugin.get_task_list()
          
          if (retval[0]):
               raise AlmException("Unable to get tasks from SD Elements." +
                              "Please ensure the application and project " +
                              "are valid and that the user has sufficient " +
                                  "permission to access the project")

          return retval[1]

     def sde_update_task_status(self, task, status):
          """ Updates the status of the given task in SD Elements

          Raises an AlmException on encountering an error

          Keyword arguments:
          task  -- An AlmTask representing the task to be updated
          status -- A string specifying the new status. Either 'Done', 'TODO',
                    or 'NA'

          """
          
          if (self.sde_plugin == None):
               logging.error("Incorrect initialization")             
               raise AlmException("Requires initialization")
          
          has_error = False
          logging.info('Attempting to update task %s to %s' % (task['id'],
                                                               status))

          retval = self.sde_plugin.api.update_task_status(task['id'], status)
          
          if (retval[0]):
               logging.error("Unable to set task because of %s, %s" %
                             (retval[0],retval[1]))
               raise AlmException("Unable to update the task status in SD" +
                                  " Elements. Either the task no longer " +
                                  "exists, there was a problem connecting " +
                                  " to the server, or the status was invalid")

          logging.info("Status for task %s successfully set in SD Elements")   

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
               if (self.sde_plugin == None):
                    raise AlmException("Requires initialization")

               #Attempt to connect to SDE & ALM
               self.sde_connect()
               self.alm_connect()

               #Attempt to get all tasks
               tasks = self.sde_get_tasks()
               logging.info("Retrieved all tasks from SDE")

               for task in tasks:
                    
                    alm_task = self.alm_get_task(task)
                    if (alm_task):
                         #Exists in both SDE & ALM
                         if (alm_task.get_status() != task['status']):
                              
                              if (self.conflict_policy == 'ALM'):
                                  #TODO: Add a check for timestamps
                                  self.sde_update_task_status(task,
                                   alm_task.get_status())
                                  pass
                                  
                              else:
                                  self.alm_update_task_status(alm_task,
                                                              task['status'])
                                  logging.info("Updated status of task " +
                                               " %s to %s in ALM"
                                               % (task['id'],alm_task.status))
                    else:
                         #Only exists in SD Elements, add it to ALM
                         self.alm_add_task(task)
                         logging.info("Added task %s to ALM" % (task['id']))

               logging.info("Synchronization complete")
               self.alm_disconnect()
                    
          except AlmException as err:
               logging.error("%s" % err)
               try:
                    self.alm_disconnect()
               except AlmException as err2:
                    logging.error("Unable to disconnect from ALM")
               print "error was encountered, please see log"


class TestAlmTask(AlmTask):

     def __init__(self, task_id, alm_id, priority, status, timestamp):
          self.task_id = task_id
          self.alm_id = alm_id
          self.priority = priority
          self.status = status
          self.timestampe = timestamp
     
     def get_task_id(self):
          return self.task_id

     def get_alm_id(self):
          return self.alm_id
     
     def get_priority(self):
          return self.priority        
          
     def get_status(self):
          return self.status       

     def get_timestamp(self):
          return self.timestamp

     
class TestAlmConnector(AlmConnector):
    """ Test class. 'Connects' to a CSV file that has a list of tasks
    """
    def alm_name(self):
          return "CSV File"

    def alm_connect(self):
          self.fields = ['id','priority','status']
          self.csv_file = open(self.configuration['file'], 'r+b')

    def alm_get_task (self, task):

          (alm_task, reader) = self.find_matching_row(task)
 
          if (alm_task):
               return TestAlmTask(alm_task['id'],
                                  '%d' % (reader.line_num),
                                  alm_task['priority'],
                                  alm_task['status'],
                                  None)
          return None

    def find_matching_row(self, task):
          reader = csv.DictReader(self.csv_file, self.fields)
          
          for row in reader:
               if (row['id'] == task['id']):
                    return (row, reader)

          return (None, reader)
          
    def alm_add_task(self, task):
          writer = csv.writer(self.csv_file, self.fields)
          writer.writerow(['%s' % task['id'], '%s' % task['priority'],
                           '%s' % task['status']])

    def alm_update_task_status(self, task, status):

          alm_task_row = self.find_matching_row(task)
 
          if (alm_task_row):
               writer = csv.DictWriter(self.csv_file, self.fields)
               writer[alm_task_row]['status'] = status
          

    def alm_disconnect(self):
          pass



def load():
    plugin = PlugInExperience(config)
    tac = TestAlmConnector(plugin, None, {'file':'test.csv'})
    tac.synchronize()

def main(argv):
    ret = config.parse_args(argv)
    if not ret:
        sys.exit(1)

    load()

if __name__ == "__main__":
    main(sys.argv)

