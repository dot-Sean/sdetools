# Copyright SDElements Inc
# Extensible two way # integration with JIRA

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


class JIRABase(APIBase):
    """ Base plugin for JIRA """

    def __init__(self, config):

        #Hack to copy over the ALM id & password for JIRA
        #authentication without overwriting the SD Elements
        #email & password in the config
        alm_config = copy.deepcopy(config)
        alm_config['email'] = alm_config['alm_id']
        alm_config['password'] = alm_config['alm_password']
        
        APIBase.__init__(self, alm_config)
        self.base_uri = '%s://%s/rest/api/2' % ((self.config['alm_method'],
                                                    self.config['alm_server']))
        
class JIRAConfig(Config):

    def set_settings(self, config):
        self.settings = config.copy()
        
class JIRATask(AlmTask):
     """
     Representation of a task in JIRA
     """
     def __init__(self, task_id, alm_id, priority,
                  status, resolution, timestamp):
          self.task_id = task_id
          self.alm_id = alm_id
          self.priority = priority
          self.status = status
          self.resolution = resolution
          self.timestamp = timestamp
     
     def get_task_id(self):
          return self.task_id

     def get_alm_id(self):
          return self.alm_id
     
     def get_priority(self):
         return self.priority        
          
     def get_status(self):
         #Translates JIRA priority into SDE priority
         
         if (self.status == 'Resolved'):    
             if (self.resolution == 'Won\'t Fix' or
                 self.resolution == 'Duplicate' or
                 self.resolution == 'Incomplete' or
                 self.resolution == 'Cannot Reproduce'):
                 return 'NA'
             else:
                 return 'DONE'
         elif (self.status == 'Closed'):
             return 'DONE'  
         else:
             #Valid 'TODO' statuses, in case we need them later:
             #'Open', 'In Progress' , 'Incomplete' 'Reopened'
             return 'TODO'      

     def get_timestamp(self):
          """ Returns a datetime object """
          return datetime.strptime(self.timestamp.split('.')[0],
                                   '%Y-%m-%dT%H:%M:%S')
    
     @classmethod
     def translate_priority(cls, priority):
        """ Translates an SDE priority into a JIRA priority """
        priority_int = 0
        try:
            priority_int = int(priority)
        except (TypeError):
            logging.error('' % priority)
            raise AlmException("Error in translating SDE priority to JIRA: " +
                               "%s is not an integer priority" % priority)
        
        if (priority_int == 10):
            return 'Blocker'
        elif (7 <= priority_int <=9):
            return 'Critical'
        elif (5 <= priority_int <=6):
            return 'Major'
        elif (3 <= priority_int <=4):
            return 'Minor'
        else:
            return 'Trivial'




class JIRAConnector(AlmConnector):
    """
     Connects to a JIRA instance
    """
    def alm_name(self):
          return "JIRA"

    def alm_connect(self):
        #No need to setup connection
        pass

    def alm_get_task (self, task):
        task_id = task['title'].partition(':')[0]
        result = None
        try:
            result = self.alm_plugin._call_api(
                'search?jql=project%%3D\'%s\'%%20AND%%20summary~\'%s\''
                                           % (self.sde_plugin.config
                                              ['alm_project'],
                                              task_id))
         
        except APIError as err: 
            logging.info(err)
            raise AlmException("Unable to get task %s from JIRA" % task_id)

        num_results = result['total']
        if (num_results == 0):
            #No result was found from query
            return None
        else:
            #We will use the first result from the query
            jtask = result['issues'][0]

            resolution = None

            if (jtask['fields']['resolution']):
                resolution = jtask['fields']['resolution']['name']
            
            return JIRATask(task['id'],
                            jtask['key'],
                            jtask['fields']['priority']['name'],
                            jtask['fields']['status']['name'],
                            resolution,
                            jtask['fields']['updated'])
            
        
       
          
    def alm_add_task(self, task):
         #Add task
         add_result = None
         try:
             add_result = self.alm_plugin._call_api('issue',
                                                         method=URLRequest.POST,
                               args={'fields':{'project':
                                    
                                      {'key':self.sde_plugin.config['alm_project']},
                                     'summary':task['title'],
                                     'description':task['content'],
                                     'priority':{'name':JIRATask.
                                                 translate_priority(
                                                     task['priority'])},  
                                     'issuetype':{'id':                                    
                                                  self.sde_plugin.config
                                                  ['jira_issue_id']}}})

         except APIError as err:
             return None
            
         trans_result = None

         if ((self.sde_plugin.config['alm_standard_workflow']=='True') and
             ((task['status']=='DONE') or task['status']=='NA')):
             try:
                 trans_result = self.alm_plugin._call_api('issue' +
                                                      '/%s/transitions' %
                                                      add_result['key'],
                                                      
                                            args={ 'transition' :
                                            
                                            {'id':self.sde_plugin.config[
                                                 'jira_close_transition']}},
                                                      
                                            method=URLRequest.POST)
             
         
             except APIError as err:
                 logging.error('Unable to change status of JIRA task: %s'
                               % err)
         
            
         #Return a unique identifier to this task in JIRA 
         return 'Issue %s' % add_result['key']

        

    def alm_update_task_status(self, task, status):

        
        if (not(task) or not(self.sde_plugin.config['alm_standard_workflow']
                             == 'True')):
            return

        trans_result = None
        try:
            if ((status=='DONE') or (status=='NA')):
                trans_result = self.alm_plugin._call_api('issue' +
                                                      '/%s/transitions' %
                                                      task.get_alm_id(),
                                                     
                                            args={ 'transition' : 
                                            {'id':self.sde_plugin.config[
                                                 'jira_close_transition']}},
                                                     
                                            method=URLRequest.POST)
            elif (status=='TODO'):
            #We are updating a closed task to TODO
                trans_result = self.alm_plugin._call_api('issue' +
                                        '/%s/transitions' %
                                        task.get_alm_id(),
                                                     
                                            args={ 'transition' : 
                                            {'id':self.sde_plugin.config[
                                                 'jira_reopen_transition']}},
                                                     
                                            method=URLRequest.POST)
        
        except APIError as err:
            logging.info("Unable to set task status: %s" % err)
                      

    def alm_disconnect(self):
          pass

def add_jira_config_options(config):
    """ Adds JIRA specific config options to the config file"""

    add_alm_config_options(config)

    config.add_custom_option('alm_standard_workflow',
                             'Standard workflow in JIRA?',
                             '-alm_standard_workflow')
    config.add_custom_option('jira_issue_id',
                             'IDs for issues raised in JIRA',
                             '-jira_issue_id')
    config.add_custom_option('jira_close_transition',
                             'Close transition in JIRA',
                             '-jira_close_transition')    
    config.add_custom_option('jira_reopen_transition',
                             'Re-open transiiton in JIRA',
                             '-jira_reopen_transition')
    
