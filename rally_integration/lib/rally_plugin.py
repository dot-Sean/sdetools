# Copyright SDElements Inc
# Extensible two way integration with Rally

import sys, os

sys.path.append(os.path.split(os.path.split(os.path.abspath(__file__))[0])[0])
from sdelib.conf_mgr import config
from sdelib.interactive_plugin import PlugInExperience
from sdelib.apiclient import APIBase, URLRequest, APIError
from alm_integration.alm_plugin_base import AlmTask, AlmConnector
from alm_integration.alm_plugin_base import AlmException, add_alm_config_options
from sdelib.conf_mgr import Config
from datetime import datetime
import logging
import copy

API_VERSION = '1.26'

class RallyAPIBase(APIBase):
    """ Base plugin for Mingle """

    def __init__(self, config):

        #Hack to copy over the ALM id & password for Mingle
        #authentication without overwriting the SD Elements
        #email & password in the config
        alm_config = copy.deepcopy(config)
        alm_config['email'] = alm_config['alm_id']
        alm_config['password'] = alm_config['alm_password']
        
        APIBase.__init__(self, alm_config)
        self.base_uri = '%s://%s/slm/webservice/%s' % ((self.config['alm_method'],
                                                    self.config['alm_server'],
                                                       API_VERSION))



class RallyConfig(Config):

    def set_settings(self, config):
        self.settings = config.copy()
        
class RallyTask(AlmTask):
     """
     Representation of a task in Rally

     Note that Rally does not have a concept
     of priorities which maps to SD Elements
     """
     def __init__(self, task_id, alm_id, alm_task_ref,
                  status, timestamp, done_statuses):
          self.task_id = task_id
          self.alm_id = alm_id

          #A Reference URL to the task in Mingle
          self.alm_task_ref = alm_task_ref
          self.status = status
          self.timestamp = timestamp
          
          #comma-separated list of done_stauses
          self.done_statuses = done_statuses
          self.carriage_return = '<br/>'
     
     def get_task_id(self):
          return self.task_id

     def get_alm_task_ref(self):
          return self.alm_task_ref

     def get_alm_id(self):
          return self.alm_id
     
     def get_priority(self):
         return self.priority        
          
     def get_status(self):
         #Translates Rally status into SDE status
         if (self.status in self.done_statuses):
             return 'DONE'  
         else:
             #Treat everything else as TODO
             return 'TODO'      

     def get_timestamp(self):
          """ Returns a datetime object """
          return datetime.strptime(self.timestamp,
                                   '%Y-%m-%dT%H:%M:%SZ')



class RallyConnector(AlmConnector):
    
    def __init__(self, sde_plugin, alm_plugin):
        """ Initializes connection to Rally """
        AlmConnector.__init__(self, sde_plugin, alm_plugin)

        self.project_ref = None
        self.workspace_ref = None

        #Verify that the configuration options are set properly
        if (not(self.sde_plugin.config['rally_done_statuses']) or
            len(self.sde_plugin.config['rally_done_statuses']) < 1):
            raise AlmException('Missing rally_done_statuses in ' +
                               'configuration')
        else:
            self.sde_plugin.config['rally_done_statuses'] = \
                self.sde_plugin.config['rally_done_statuses'].split(',')

        if (not(self.sde_plugin.config['alm_standard_workflow'])):
            raise AlmException('Missing alm_standard_workflow in configuration')

        if (not(self.sde_plugin.config['rally_card_type'])):
            raise AlmException('Missing rally_card_type in configuration')

        if (not(self.sde_plugin.config['rally_new_status'])):
            raise AlmException('Missing rally_card_type in configuration')

        if (not(self.sde_plugin.config['rally_workspace'])):
            raise AlmException('Missing rally_workspace in configuration')

    def carriage_return(self):
          return '<br//>'
    
    def alm_name(self):
          return 'Rally'

    def alm_connect(self):
        """ Verifies that Ming connection works """
        #Check to make sure that we can do a simple API call
        try:
            result = self.alm_plugin._call_api('task.js')
        except APIError as err:
            raise AlmException('Unable to connnect to Rally. Please' +
                               ' check server URL, ID, password and project')

        #Now try to get workspace ID
        
        try:
            workspace_ref = self.alm_plugin._call_api('workspace.js',
                                               args={'query':
                                                     '(Name = \"%s\")' %
                                                 self.sde_plugin.config[
                                                     'rally_workspace']})
            num_results = workspace_ref['QueryResult']['TotalResultCount']
            if (num_results == 0):
                raise AlmException('Workspace is not valid, please check' +
                                   'config value: %s' % self.sde_plugin.config[
                                                     'rally_workspace'])
            workspace_ref = workspace_ref['QueryResult']['Results'][0]
            workspace_ref =  workspace_ref['_ref']
            self.workspace_ref = workspace_ref
            
        except APIError as err:
            raise AlmException('Unable to connnect to Rally. Please' +
                               ' check server URL, ID, password and project')


        #Now get project ID
        try:
            project_ref = self.alm_plugin._call_api('project.js',
                                               args={'query':
                                                     '(Name = \"%s\")' %
                                                 self.sde_plugin.config[
                                                     'alm_project']})
            num_results = project_ref['QueryResult']['TotalResultCount']
            if (num_results == 0):
                raise AlmException('Rally project is not valid, please check' +
                                   'config value: %s' % self.sde_plugin.config[
                                                     'alm_project'])
            project_ref = project_ref['QueryResult']['Results'][0]
            project_ref =  project_ref['_ref']
            self.project_ref = project_ref
        
        except APIError as err:
            raise AlmException('Unable to connnect to Rally. Please' +
                               ' check server URL, ID, password and project')

        

    def alm_get_task (self, task):
        task_id = task['title']
        result = None

        try:
            query_string = '(Name = \"%s\")' % task_id
            result = self.alm_plugin._call_api('hierarchicalrequirement.js',
                                               args = {'query':
                                                       query_string })
        except APIError as err: 
            logging.info('Error is %s:' % err)
            raise AlmException('Unable to get task %s from Rally' % task_id)

        
        num_results = result['QueryResult']['TotalResultCount']
        
        
        if (num_results != 0):
            try:
                
                task_result_url =  result['QueryResult']['Results'][0]
                task_result_url = task_result_url['_ref']
                task_result_url = task_result_url.split('/%s/' % API_VERSION)[1]
                task_data = self.alm_plugin._call_api(task_result_url)
                task_data = task_data['HierarchicalRequirement']
                return RallyTask(task_id,
                                 task_data['FormattedID'],
                                 task_data['_ref'].split('/%s/' % API_VERSION)[1],
                                 task_data['ScheduleState'],
                                 task_data['LastUpdateDate'],
                              self.sde_plugin.config['rally_done_statuses'])
            except Exception as err:
                logging.info('Error is %s:' % err)
                raise AlmException('Unable to get card # for task '  +
                                   '%s from Rally' % task_id)

        else:
            return None

            
        
       
          
    def alm_add_task(self, task):
         
         add_result = None

         #First check to see if task exists
         try:
             if self.alm_get_task(task):
                 logging.debug('Task %s already exists in Rally Project'
                               % task['id'])
                 return None
             #Task does exist, so quick
         except AlmException:
             #This means task doesn't exist, which is correct
             pass
         try:
             result= self.alm_plugin._call_api(
                 'hierarchicalrequirement/create.js',
                                    method=URLRequest.POST,
                                args = { 'HierarchicalRequirement' : {'Name':task['title'],
                                         'Description':
                                             self.sde_get_task_content(task),
                                         'Workspace':
                                             self.workspace_ref,
                                         'Project':
                                            self.project_ref}})
             logging.debug('Task %s added to Rally Project' %
                          task['id'])
         except APIError as err:
             raise AlmException('Please check ALM-specific settings in config ' +
                                'file. Unable to add task ' +
                                '%s because of %s' % (task['id'], err))
             
            
         #Return a unique identifier to this task in Rally
         alm_task = self.alm_get_task(task)
         if not(alm_task):
             raise AlmException('Alm task not added sucessfully. Please ' +
                                'check ALM-specific settings in config file')

            
         if ((self.sde_plugin.config['alm_standard_workflow']=='True') and
             ((task['status']=='DONE') or task['status']=='NA')):
             self.alm_update_task_status(alm_task, task['status'])   
         return 'Project: %s, Story: %s' % (self.sde_plugin.config['alm_project'],
                                         alm_task.get_alm_id())


    def alm_update_task_status(self, task, status):
        
        if (not(task) or not(self.sde_plugin.config['alm_standard_workflow']
                             == 'True')):
            logging.debug('Status synchronization disabled')
            return

        trans_result = None

        if ((status=='DONE') or (status=='NA')):
            try:
                result = self.alm_plugin._call_api(task.get_alm_task_ref(),
                                       args = {'HierarchicalRequirement' :
                                               {'ScheduleState':
                                        self.sde_plugin.config[
                                         'rally_done_statuses'][0]}},
                                          method=URLRequest.POST)
            except APIError as err:
                raise AlmException('Unable to update task status to DONE' +
                                   ' for card: ' +
                             '%s in Rally because of %s' % (task.get_alm_id(),
                              err))
                
        elif (status=='TODO'):
            try:
                self.alm_plugin._call_api(task.get_alm_task_ref(),
                                       args = {'HierarchicalRequirement' :   
                                           {'ScheduleState':
                                        self.sde_plugin.config[
                                         'rally_new_status']}},
                                          method=URLRequest.POST)
            except APIError as err:
                raise AlmException('Unable to update task status to TODO' +
                                   ' for card:' +
                             ' %s in Rally because of %s' % (task.get_alm_id(),
                              err))

        logging.debug('Status changed to %s for task %s in Rally' %
                      (status, task.get_alm_id()))
                    
                    
                      

    def alm_disconnect(self):
          pass

def add_rally_config_options(config):
    """ Adds Rally specific config options to the config file"""

    add_alm_config_options(config)

    config.add_custom_option('alm_standard_workflow',
                             'Standard workflow in Rally?',
                             '-alm_standard_workflow')
    config.add_custom_option('rally_card_type',
                             'IDs for issues raised in Rally',
                             '-rally_card_type')
    config.add_custom_option('rally_new_status',
                             'status to set for new tasks in Rally',
                             '-rally_new_status')
    config.add_custom_option('rally_done_statuses',
                             'Done statuses in Rally',
                             '-rally_done_statuses')
    config.add_custom_option('rally_workspace',
                             'Rally Workspace',
                             '-rally_workspace') 
