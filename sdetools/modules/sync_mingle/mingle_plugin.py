# Copyright SDElements Inc
# Extensible two way integration with Mingle

import urllib
from datetime import datetime
from sdetools.extlib.defusedxml import minidom

from sdetools.sdelib.restclient import RESTBase
from sdetools.sdelib.restclient import URLRequest, APIError
from sdetools.alm_integration.alm_plugin_base import AlmTask, AlmConnector
from sdetools.alm_integration.alm_plugin_base import AlmException
from sdetools.sdelib.conf_mgr import Config
from sdetools.extlib import markdown

from sdetools.sdelib import log_mgr
logger = log_mgr.mods.add_mod(__name__)

class MingleAPIBase(RESTBase):
    def __init__(self, config):
        super(MingleAPIBase, self).__init__('alm', 'Mingle', config, 'api/v2')

    def encode_post_args(self, args):
        encoded_args = dict((key.encode('utf-8'), val.encode('utf-8')) for key, val in args.items())
        return urllib.urlencode(encoded_args)

    def parse_response(self, result): 
        if result:
            try:
                result = minidom.parseString(result)
            except Exception, err:
                # This means that the result doesn't have XML, not an error
                pass
        return result

    def set_content_type(self, req, method):
        pass

class MingleTask(AlmTask):
    """ Representation of a task in Mingle"""

    def __init__(self, task_id, alm_id, status, timestamp, done_statuses):
        self.task_id = task_id
        self.alm_id = alm_id
        self.status = status
        self.timestamp = timestamp
        self.done_statuses = done_statuses  # comma-separated list
        self.priority = None

    def get_task_id(self):
        return self.task_id

    def get_alm_id(self):
        return self.alm_id

    def get_priority(self):
        return self.priority

    def get_status(self):
        """ Translates Mingle status into SDE status """
        if self.status in self.done_statuses:
            return 'DONE'
        else:
            return 'TODO'

    def get_timestamp(self):
        """ Returns a datetime object """
        return datetime.strptime(self.timestamp,
                                 '%Y-%m-%dT%H:%M:%SZ')

class MingleConnector(AlmConnector):
    alm_name = 'Mingle'

    def __init__(self, config, alm_plugin):
        """ Initializes connection to Mingle """
        super(MingleConnector, self).__init__(config, alm_plugin)

        config.add_custom_option('mingle_card_type', 'IDs for issues raised in Mingle',
            default='Story')
        config.add_custom_option('mingle_new_status', 'Status to set for new tasks in Mingle',
            default='Ready for Analysis')
        config.add_custom_option('mingle_done_statuses', 'Statuses that signify a task is Done in Mingle',
            default='Ready for Testing,In Testing,Ready for Signoff,Accepted')

    def initialize(self):
        super(MingleConnector, self).initialize()

        #Verify that the configuration options are set properly
        if (not self.sde_plugin.config['mingle_done_statuses'] or
            len(self.sde_plugin.config['mingle_done_statuses']) < 1):
            raise AlmException('Missing mingle_done_statuses in configuration')

        self.config.process_list_config('mingle_done_statuses')

        if not self.sde_plugin.config['mingle_card_type']:
            raise AlmException('Missing mingle_card_type in configuration')
        if not self.sde_plugin.config['mingle_new_status']:
            raise AlmException('Missing mingle_card_type in configuration')

        self.mark_down_converter = markdown.Markdown(safe_mode="escape")

    def alm_connect_server(self):
        try:
            self.alm_plugin.call_api('projects.xml')
        except APIError, err:
            raise AlmException('Unable to connect to Mingle. Please '
                               'check server URL, ID, password. Reason: %s' % err)

    def alm_connect_project(self):
        """ Verifies that Mingle connection works """
        self.project_uri = 'projects/%s/cards' % (
                self.alm_plugin.urlencode_str(self.config['alm_project']))

        #Check to make sure that we can do a simple API call
        try:
            self.alm_plugin.call_api('%s.xml' % self.project_uri)
        except APIError, err:
            raise AlmException('Unable to find Mingle project. Reason: %s' % err)

    def alm_get_task(self, task):
        task_id = task['title']
        result = None

        try:
            task_args =  {'filters[]': ('[Name][is][%s]' % task_id)}
            result = self.alm_plugin.call_api('%s.xml' % self.project_uri, args=task_args)
        except APIError, err:
            logger.error(err)
            raise AlmException('Unable to get task %s from Mingle' % task_id)

        card_element =  result.getElementsByTagName('card')
        if not card_element.length:
            return None

        card_item = card_element.item(0)
        try:
            card_num = card_item.getElementsByTagName(
                    'number').item(0).firstChild.nodeValue
        except Exception, err:
            logger.info(err)
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
                    if status_node:
                        status = status_node.nodeValue
                    else:
                        status = 'TODO'
                    break
        return MingleTask(task_id, card_num, status, modified_date,
                          self.sde_plugin.config['mingle_done_statuses'])

    def alm_add_task(self, task):
        try:
            status_args = {
                'card[name]': task['title'],
                'card[card_type_name]': self.sde_plugin.config['mingle_card_type'],
                'card[description]': self.sde_get_task_content(task),
                'card[properties][][name]': 'status',
                'card[properties][][value]': self.sde_plugin.config['mingle_new_status']
            }
            self.alm_plugin.call_api('%s.xml' % self.project_uri, args=status_args,
                    method=URLRequest.POST)
            logger.debug('Task %s added to Mingle Project' % task['id'])
        except APIError, err:
            raise AlmException('Please check ALM-specific settings in config '
                    'file. Unable to add task %s because of %s' %
                    (task['id'], err))

        #Return a unique identifier to this task in Mingle
        alm_task = self.alm_get_task(task)
        if not alm_task:
            raise AlmException('Alm task not added sucessfully. Please '
                               'check ALM-specific settings in config file')

        if (self.sde_plugin.config['alm_standard_workflow'] and
                (task['status']=='DONE' or task['status']=='NA')):
            self.alm_update_task_status(alm_task, task['status'])
        return 'Project: %s, Card: %s' % (self.sde_plugin.config['alm_project'],
                                          alm_task.get_alm_id())


    def alm_update_task_status(self, task, status):
        if not task or not self.sde_plugin.config['alm_standard_workflow']:
            logger.debug('Status synchronization disabled')
            return

        if status == 'DONE' or status=='NA':
            try:
                status_args = {
                    'card[properties][][name]':'status',
                    'card[properties][][value]': self.sde_plugin.config['mingle_done_statuses'][0]
                }
                self.alm_plugin.call_api('%s/%s.xml' % (self.project_uri, task.get_alm_id()),
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
                self.alm_plugin.call_api('%s/%s.xml' % (self.project_uri, task.get_alm_id()),
                        args=status_args, method=URLRequest.PUT)
            except APIError, err:
                raise AlmException('Unable to update task status to TODO for '
                                   'card: %s in Mingle because of %s' %
                                   (task.get_alm_id(), err))
        logger.debug('Status changed to %s for task %s in Mingle' %
                (status, task.get_alm_id()))

    def alm_disconnect(self):
        pass

    def convert_markdown_to_alm(self, content, ref): 
        return self.mark_down_converter.convert(content)
