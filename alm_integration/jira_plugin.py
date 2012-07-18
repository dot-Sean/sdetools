#!/usr/bin/python
#
# Version 0.01
# Rohit Sethi
# Copyright SDElements Inc
#
# Extensible two way # integration with JIRA

import sys, os
sys.path.append(os.path.split(os.path.split(os.path.abspath(__file__))[0])[0])

from sdelib.conf_mgr import config
from sdelib.interactive_plugin import PlugInExperience
from sdelib.apiclient import APIBase, URLRequest
from alm_plugin_base import AlmException, AlmTask, AlmConnector 
from sdelib.conf_mgr import Config
from datetime import datetime
import logging


class JIRABase(APIBase):
    """ Base plugin for JIRA """

    def __init__(self, config):
        APIBase.__init__(self, config)
        self.base_uri = '%s://%s/rest/api/2' % ((self.config['method'],
                                                    self.config['server']))
        
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
        ret_err, ret_val = self.alm_plugin._call_api(
            'search?jql=project%%3D\'%s\'%%20AND%%20summary~\'%s\''
                                           % (self.configuration['project'],
                                              task_id))
         
        if (ret_err):
            logging.info("Error return: %s, %s" % (ret_err, ret_val))
            raise AlmException("Unable to get task %s from JIRA" % task['id'])

        num_results = ret_val['total']
        if (num_results == 0):
            #No result was found from query
            return None
        else:
            #We will use the first result from the query
            jtask = ret_val['issues'][0]

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
         add_err, add_result = self.alm_plugin._call_api('issue',
                                                         method=URLRequest.POST,
                               args={'fields':{'project':
                                      {'key':self.configuration['project']},
                                     'summary':task['title'],
                                     'description':task['content'],
                                     'priority':{'name':JIRATask.
                                                 translate_priority(
                                                     task['priority'])},  
                                     'issuetype':{'id':self.
                                                  configuration['issue_id']}}})

         if (add_err):
             return None
            
         trans_err, trans_result = 0, 0
         if (self.configuration['standard_workflow'] and
             ((task['status']=='DONE') or task['status']=='NA')):
             logging.debug('Attempting to set a task status to %s' %
                          task['status'])
             trans_err,
             trans_result = self.alm_plugin._call_api('issue' +
                                                      '/%s/transitions' %
                                                      add_result['key'],
                                                      
                                            args={ 'transition' :
                                            {'id':self.configuration[
                                                 'close_transition']}},
                                                      
                                            method=URLRequest.POST)
             
             logging.debug('setting err %s and result %s' % (trans_err,
                                                            trans_result))
         
         if (trans_err):
             logging.info("Unable to change status of JIRA task: %s, %s" % (
                 trans_err, trans_val))
         
            
         #Return a unique identifier to this task in JIRA 
         return "Issue %s" % add_result['key']

        

    def alm_update_task_status(self, task, status):

     
        if (not(task) or not(self.configuration['standard_workflow'])):
            return

        trans_err, trans_result = None, None
        if ((status=='DONE') or (status=='NA')):
            trans_err,
            trans_result = self.alm_plugin._call_api('issue' +
                                                      '/%s/transitions' %
                                                      task.get_alm_id(),
                                                     
                                            args={ 'transition' :
                                            {'id':self.configuration[
                                                 'close_transition']}},
                                                     
                                            method=URLRequest.POST)
        elif (status=='TODO'):
            #We are updating a closed task to TODO
            trans_err,
            trans_result = self.alm_plugin._call_api('issue' +
                                                      '/%s/transitions' %
                                                      task.get_alm_id(),
                                                     
                                            args={ 'transition' :
                                            {'id':self.configuration[
                                                 'reopen_transition']}},
                                                     
                                            method=URLRequest.POST)
        logging.debug('setting err %s and result %s' % (trans_err,
                                                            trans_result))
        if (trans_err):
            logging.info("Unable to set task status: %s, %s" % (trans_err,
                                                                trans_val))
            
             
          
          

    def alm_disconnect(self):
          pass
