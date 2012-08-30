# Copyright SDElements Inc
# Extensible two way integration with Mingle

import sys, os

sys.path.append(os.path.split(os.path.split(os.path.abspath(__file__))[0])[0])
from sdelib.apiclient import URLRequest, APIError
from alm_integration.alm_plugin_base import AlmTask, AlmConnector
from alm_integration.alm_plugin_base import AlmException, add_alm_config_options
from sdelib.conf_mgr import Config
from datetime import datetime
import logging


class MingleConfig(Config):
    def set_settings(self, config):
        self.settings = config.copy()

class MingleTask(AlmTask):
    """ Representation of a task in Mingle"""

    def __init__(self, task_id, alm_id, status, timestamp, done_statuses):
        self.task_id = task_id
        self.alm_id = alm_id
        self.status = status
        self.timestamp = timestamp
        self.done_statuses = done_statuses  # comma-separated list

    def get_task_id(self):
        return self.task_id

    def get_alm_id(self):
        return self.alm_id

    def get_priority(self):
        return self.priority

    def get_status(self):
        """ Translates Mingle status into SDE status """
        return 'DONE' if self.status in self.done_statuses else 'TODO'

    def get_timestamp(self):
        """ Returns a datetime object """
        return datetime.strptime(self.timestamp,
                                 '%Y-%m-%dT%H:%M:%SZ')

class MingleConnector(AlmConnector):

    def __init__(self, sde_plugin, alm_plugin):
        """ Initializes connection to Mingle """
        AlmConnector.__init__(self, sde_plugin, alm_plugin)

        #Verify that the configuration options are set properly
        if (not self.sde_plugin.config['mingle_done_statuses'] or
            len(self.sde_plugin.config['mingle_done_statuses']) < 1):
            raise AlmException('Missing mingle_done_statuses in configuration')

        self.sde_plugin.config['mingle_done_statuses'] =  (
                self.sde_plugin.config['mingle_done_statuses'].split(','))

        if not self.sde_plugin.config['alm_standard_workflow']:
            raise AlmException('Missing alm_standard_workflow in configuration')
        if not self.sde_plugin.config['mingle_card_type']:
            raise AlmException('Missing mingle_card_type in configuration')
        if not self.sde_plugin.config['mingle_new_status']:
            raise AlmException('Missing mingle_card_type in configuration')

    def alm_name(self):
        return 'Mingle'

    def alm_connect(self):
        """ Verifies that Mingle connection works """
        #Check to make sure that we can do a simple API call
        try:
            self.alm_plugin._call_api('cards.xml')
        except APIError:
            raise AlmException('Unable to connnect to Mingle. Please '
                               'check server URL, ID, password and '
                               'project')

    def alm_get_task (self, task):
        task_id = task['title']
        result = None

        try:
            task_args =  {'filters[]': ('[Name][is][%s]' % task_id)}
            result = self.alm_plugin._call_api('cards.xml', args=task_args)
        except APIError, err:
            logging.error(err)
            raise AlmException('Unable to get task %s from Mingle' % task_id)

        card_element =  result.getElementsByTagName('card')
        if not card_element.length:
            return None

        card_item = card_element.item(0)
        try:
            card_num = card_item.getElementsByTagName(
                    'number').item(0).firstChild.nodeValue
        except Exception, err:
            logging.info(err)
            raise AlmException('Unable to get card # for task '
                               '%s from Mingle' % task_id)
        modified_date  = None
        if card_item.getElementsByTagName('modified_on'):
            modified_date = card_item.getElementsByTagName(
                    'modified_on').item(0).firstChild.nodeValue
        status = None
        if card_item.getElementsByTagName('property'):
            properties = card_item.getElementsByTagName('property')
            for prop in properties:
                if (prop.getElementsByTagName(
                            'name').item(0).firstChild.nodeValue ==
                            'Status'):
                    status_node = prop.getElementsByTagName(
                            'value').item(0).firstChild
                    status = status_node.nodeValue if status_node else 'TODO'
                    break
        return MingleTask(task_id, card_num, status, modified_date,
                          self.sde_plugin.config['mingle_done_statuses'])

    def alm_add_task(self, task):
        #First check to see if task exists
        try:
            if self.alm_get_task(task):
                logging.debug('Task %s already exists in Mingle Project'
                              % task['id'])
                return None
        except AlmException:
            #This means task doesn't exist, which is expected
            pass
        try:
            status_args = {
                'card[name]': task['title'],
                'card[card_type_name]': self.sde_plugin.config['mingle_card_type'],
                'card[description]': self.sde_get_task_content(task),
                'card[properties][][name]': 'status',
                'card[properties][][value]': self.sde_plugin.config['mingle_new_status']
            }
            self.alm_plugin._call_api('cards.xml', args=status_args,
                    method=URLRequest.POST)
            logging.debug('Task %s added to Mingle Project' % task['id'])
        except APIError, err:
            raise AlmException('Please check ALM-specific settings in config '
                    'file. Unable to add task %s because of %s' %
                    (task['id'], err))

        #Return a unique identifier to this task in Mingle
        alm_task = self.alm_get_task(task)
        if not alm_task:
            raise AlmException('Alm task not added sucessfully. Please '
                               'check ALM-specific settings in config file')

        if (self.sde_plugin.config['alm_standard_workflow']=='True' and
                (task['status']=='DONE' or task['status']=='NA')):
            self.alm_update_task_status(alm_task, task['status'])
        return 'Project: %s, Card: %s' % (self.sde_plugin.config['alm_project'],
                                          alm_task.get_alm_id())


    def alm_update_task_status(self, task, status):
        if not task or not self.sde_plugin.config['alm_standard_workflow'] == 'True':
            logging.debug('Status synchronization disabled')
            return

        if status == 'DONE' or status=='NA':
            try:
                status_args = {
                    'card[properties][][name]':'status',
                    'card[properties][][value]': self.sde_plugin.config['mingle_done_statuses'][0]
                }
                self.alm_plugin._call_api('cards/%s.xml' % task.get_alm_id(),
                        args=status_args, method=URLRequest.PUT)
            except APIError, err:
                raise AlmException('Unable to update task status to DONE '
                                   'for card: %s in Mingle because of %s' %
                                   (task.get_alm_id(),err))
        elif status== 'TODO':
            try:
                status_args = {
                    'card[properties][][name]':'status',
                    'card[properties][][value]': self.sde_plugin.config['mingle_new_status']
                }
                self.alm_plugin._call_api('cards/%s.xml' % task.get_alm_id(),
                        args=status_args, method=URLRequest.PUT)
            except APIError, err:
                raise AlmException('Unable to update task status to TODO for '
                                   'card: %s in Mingle because of %s' %
                                   (task.get_alm_id(), err))
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
