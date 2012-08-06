# Copyright SDElements Inc
# Extensible two way integration with Mingle

import sys, os

sys.path.append(os.path.split(os.path.split(os.path.abspath(__file__))[0])[0])
from sdelib.conf_mgr import config
from sdelib.interactive_plugin import PlugInExperience
from sdelib.apiclient import APIBase, URLRequest, APIError
from alm_integration.alm_plugin_base import AlmTask, AlmConnector
from alm_integration.alm_plugin_base import AlmException, add_alm_config_options
from mingle_integration.bin.mingle_apiclient import MingleAPIBase
from sdelib.conf_mgr import Config
from datetime import datetime
import logging
import copy


class MingleConfig(Config):

    def set_settings(self, config):
        self.settings = config.copy()
        
class MingleTask(AlmTask):
     """
     Representation of a task in Mingle

     Note that Mingle does not have a concept
     of priorities which maps to SD Elements
     """
     def __init__(self, task_id, alm_id, 
                  status, timestamp, done_statuses):
          self.task_id = task_id
          self.alm_id = alm_id
          self.status = status
          self.timestamp = timestamp
          #comma-separated list of done_stauses
          self.done_statuses = done_statuses
     
     def get_task_id(self):
          return self.task_id

     def get_alm_id(self):
          return self.alm_id
     
     def get_priority(self):
         return self.priority        
          
     def get_status(self):
         #Translates Mingle status into SDE status
         if (self.status in self.done_statuses):
             return 'DONE'  
         else:
             #Treat everything else as TODO
             return 'TODO'      

     def get_timestamp(self):
          """ Returns a datetime object """
          return datetime.strptime(self.timestamp,
                                   '%Y-%m-%dT%H:%M:%SZ')



class MingleConnector(AlmConnector):
    
    def __init__(self, sde_plugin, alm_plugin):
        """ Initializes connection to Mingle """
        AlmConnector.__init__(self, sde_plugin, alm_plugin)

        #Verify that the configuration options are set properly
        if (not(self.sde_plugin.config['mingle_done_statuses']) or
            len(self.sde_plugin.config['mingle_done_statuses']) < 1):
            raise AlmException('Missing mingle_done_statuses in ' +
                               'configuration')
        else:
            self.sde_plugin.config['mingle_done_statuses'] = \
                self.sde_plugin.config['mingle_done_statuses'].split(',')

        if (not(self.sde_plugin.config['alm_standard_workflow'])):
            raise AlmException('Missing alm_standard_workflow in configuration')

        if (not(self.sde_plugin.config['mingle_card_type'])):
            raise AlmException('Missing mingle_card_type in configuration')

        if (not(self.sde_plugin.config['mingle_new_status'])):
            raise AlmException('Missing mingle_card_type in configuration')
    
    def alm_name(self):
          return 'Mingle'

    def alm_connect(self):
        """ Verifies that Ming connection works """
        #Check to make sure that we can do a simple API call
        try:
            result = self.alm_plugin._call_api('cards.xml')
        except APIError as err:
            raise AlmException('Unable to connnect to Mingle. Please' +
                               ' check server URL, ID, password and project')

    def alm_get_task (self, task):
        task_id = task['title']
        result = None
        #logging.debug('Attempting to get task %s in Mingle ' %
        #                  task_id)
        try:
            result = self.alm_plugin._call_api('cards.xml',
                                               args = {'filters[]':
                                                       ('[Name][is][' +
                                                       '%s]' % task_id)})
        except APIError as err: 
            logging.info(err)
            raise AlmException('Unable to get task %s from Mingle' % task_id)

        card_element =  result.getElementsByTagName('card')
        card_num = None
        modified_date  = None
        status = None
        if (card_element.length > 0):
            try:
                card_num =  card_element.item(0).getElementsByTagName(
                    'number').item(0).firstChild.nodeValue
            except Exception as err:
                logging.info(err)
                raise AlmException('Unable to get card # for task'  +
                                   '%s from Mingle' % task_id)

            
            if (card_element.item(0).getElementsByTagName(
                    'modified_on')):
                modified_date =  card_element.item(0).getElementsByTagName(
                    'modified_on').item(0).firstChild.nodeValue

            if (card_element.item(0).getElementsByTagName(
                    'property')):
                
                properties = card_element.item(0).getElementsByTagName(
                    'property')
                for task_prop in properties:
                    if (task_prop.getElementsByTagName(
                        'name').item(0).firstChild.nodeValue
                        == 'Status'):
                        status_node = task_prop.getElementsByTagName(
                        'value').item(0).firstChild
                        if (status_node):
                            status = status_node.nodeValue
                        else:
                            status = 'TODO'
                        break
            return MingleTask(task_id, card_num, status, modified_date,
                              self.sde_plugin.config['mingle_done_statuses'])
        else:
            return None

            
        
       
          
    def alm_add_task(self, task):
         
         add_result = None

         #First check to see if task exists
         try:
             if self.alm_get_task(task):
                 logging.debug('Task %s already exists in Mingle Project'
                               % task['id'])
                 return None
             #Task does exist, so quick
         except AlmException:
             #This means task doesn't exist, which is correct
             pass
         try:
             self.alm_plugin._call_api('cards.xml',
                                    method=URLRequest.POST,
                                args = { 'card[name]':task['title'],
                                         'card[card_type_name]':
                                             self.sde_plugin.config[
                                                 'mingle_card_type'],
                                         'card[description]':
                                             self.sde_get_task_content(task),
                                         'card[properties][][name]':
                                                 'status',
                                         'card[properties][][value]':
                                                self.sde_plugin.config[
                                                 'mingle_new_status']})
             logging.debug('Task %s added to Mingle Project' %
                          task['id'])
         except APIError as err:
             raise AlmException('Please check ALM-specific settings in config ' +
                                'file. Unable to add task ' +
                                '%s because of %s' % (task['id'], err))
             
            
         #Return a unique identifier to this task in Mingle
         alm_task = self.alm_get_task(task)
         if not(alm_task):
             raise AlmException('Alm task not added sucessfully. Please ' +
                                'check ALM-specific settings in config file')

            
         if ((self.sde_plugin.config['alm_standard_workflow']=='True') and
             ((task['status']=='DONE') or task['status']=='NA')):
             self.alm_update_task_status(alm_task, task['status'])   
         return 'Project: %s, Card: %s' % (self.sde_plugin.config['alm_project'],
                                         alm_task.get_alm_id())


    def alm_update_task_status(self, task, status):
        
        if (not(task) or not(self.sde_plugin.config['alm_standard_workflow']
                             == 'True')):
            logging.debug('Status synchronization disabled')
            return

        trans_result = None

        if ((status=='DONE') or (status=='NA')):
            try:
                self.alm_plugin._call_api('cards/%s.xml' % task.get_alm_id(),
                                          
                                       args = {'card[properties][][name]':
                                         'status',
                                                'card[properties][][value]':
                                        self.sde_plugin.config[
                                         'mingle_done_statuses'][0]},
                                          method=URLRequest.PUT)
            except APIError as err:
                raise AlmException('Unable to update task status to DONE' +
                                   ' for card: ' +
                             '%s in Mingle because of %s' % (task.get_alm_id(),
                              err))
                
        elif (status=='TODO'):
            try:
                self.alm_plugin._call_api('cards/%s.xml' % task.get_alm_id(),
                                          
                                       args = {'card[properties][][name]':
                                         'status',
                                                'card[properties][][value]':
                                        self.sde_plugin.config[
                                         'mingle_new_status']},
                                          method=URLRequest.PUT)
            except APIError as err:
                raise AlmException('Unable to update task status to TODO' +
                                   ' for card:' +
                             ' %s in Mingle because of %s' % (task.get_alm_id(),
                              err))

        logging.debug('Status changed to %s for task %s in Mingle' %
                      (status, task.get_alm_id()))
                    
                    
                      

    def alm_disconnect(self):
          pass

def add_mingle_config_options(config):
    """ Adds Mingle specific config options to the config file"""

    add_alm_config_options(config)

    config.add_custom_option('alm_standard_workflow',
                             'Standard workflow in Mingle?',
                             '-alm_standard_workflow')
    config.add_custom_option('mingle_card_type',
                             'IDs for issues raised in Mingle',
                             '-mingle_card_type')
    config.add_custom_option('mingle_new_status',
                             'status to set for new tasks in Mingle',
                             '-mingle_new_status')
    config.add_custom_option('mingle_done_statuses',
                             'Done statuses in Mingle',
                             '-mingle_done_statuses')    
