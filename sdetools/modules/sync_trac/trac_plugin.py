# Copyright SDElements Inc
# Extensible two way integration with Trac

import xmlrpclib

from sdetools.sdelib.restclient import RESTBase
from sdetools.sdelib.restclient import URLRequest, APIError
from sdetools.alm_integration.alm_plugin_base import AlmTask, AlmConnector
from sdetools.alm_integration.alm_plugin_base import AlmException

from sdetools.sdelib import log_mgr
logger = log_mgr.mods.add_mod(__name__)

class TracXMLRPCAPI(RESTBase):
    def __init__(self, config):
        super(TracXMLRPCAPI, self).__init__('alm', 'Trac', config, 'login/xmlrpc')
        self.proxy = None

    def post_conf_init(self):
        self.server = self._get_conf('server') 
        self.base_uri = '%s://%s:%s@%s/%s' % (
            self._get_conf('method'), 
            self._get_conf('user'),
            self._get_conf('pass'),
            self.server, 
            self.base_path)

    def connect(self):
        if self.proxy:
            return
        self.post_conf_init()
        self.proxy = xmlrpclib.ServerProxy(self.base_uri)

class TracTask(AlmTask):
    """ Representation of a task in Trac"""

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
        if self.status in self.done_statuses:
            return 'DONE'
        else:
            return 'TODO'

    def get_timestamp(self):
        """ Returns a datetime object """
        return datetime.strptime(self.timestamp,
                                 '%Y-%m-%dT%H:%M:%SZ')

class TracConnector(AlmConnector):
    alm_name = 'Trac'

    def __init__(self, config, alm_plugin):
        """ Initializes connection to Trac """
        super(TracConnector, self).__init__(config, alm_plugin)

        config.add_custom_option('alm_standard_workflow', 'Standard workflow in Trac?',
            default='True')
        config.add_custom_option('trac_card_type', 'IDs for issues raised in Trac',
            default='Story')
        config.add_custom_option('trac_new_status', 'Status to set for new tasks in Trac',
            default='Ready for Analysis')
        config.add_custom_option('trac_done_statuses', 'Statuses that signify a task is Done in Trac',
            default='Ready for Testing,In Testing,Ready for Signoff,Accepted')
        self.alm_task_title_prefix = 'SDE '

    def initialize(self):
        super(TracConnector, self).initialize()

        #Verify that the configuration options are set properly
        if (not self.sde_plugin.config['trac_done_statuses'] or
            len(self.sde_plugin.config['trac_done_statuses']) < 1):
            raise AlmException('Missing trac_done_statuses in configuration')

        self.sde_plugin.config['trac_done_statuses'] =  (
                self.sde_plugin.config['trac_done_statuses'].split(','))

        if not self.sde_plugin.config['alm_standard_workflow']:
            raise AlmException('Missing alm_standard_workflow in configuration')
        if not self.sde_plugin.config['trac_card_type']:
            raise AlmException('Missing trac_card_type in configuration')
        if not self.sde_plugin.config['trac_new_status']:
            raise AlmException('Missing trac_card_type in configuration')

    def alm_connect(self):
        """ Perform initial connect and verify that Trac connection works """
        self.alm_plugin.connect()

    def _vet_alm_tasks(self, tasks):
        return tasks[0]

    def alm_get_task(self, task):
        task_id = task['title'].partition(':')[0]
        
        qstr = 'summary^=%s%s' % (self.alm_task_title_prefix, task_id)
        result = self.alm_plugin.proxy.ticket.query(qstr)
        if not result:
            return None

        alm_id = self._vet_alm_tasks(self, tasks)

        trac_task = self.alm_plugin.proxy.ticket.get(alm_id)

        return TracTask(task_id, alm_id, trac_task['status'], trac_task['changetime'],
                          self.sde_plugin.config['trac_done_statuses'])

    def alm_add_task(self, task):
        title = '%s%s' % (self.alm_task_title_prefix, task['title'])

        alm_id = self.alm_plugin.proxy.ticket.create(
            title,
            self.sde_get_task_content(task))
#            attributes={
#                'status': self.sde_plugin.config['trac_new_status']
#                })

        if not alm_id:
            raise AlmException('Alm task not added sucessfully. Please '
                               'check ALM-specific settings in config file')
        alm_task = self.alm_plugin.proxy.ticket.get(alm_id)

        if (self.sde_plugin.config['alm_standard_workflow']=='True' and
                (task['status']=='DONE' or task['status']=='NA')):
            self.alm_update_task_status(alm_task, task['status'])
        return 'Project: %s, Card: %s' % (self.sde_plugin.config['alm_project'],
                                          alm_task.get_alm_id())


    def alm_update_task_status(self, task, status):
        if not task or not self.sde_plugin.config['alm_standard_workflow'] == 'True':
            logger.debug('Status synchronization disabled')
            return

        if status == 'DONE' or status=='NA':
            try:
                status_args = {
                    'card[properties][][name]':'status',
                    'card[properties][][value]': self.sde_plugin.config['trac_done_statuses'][0]
                }
                self.alm_plugin.call_api('cards/%s.xml' % task.get_alm_id(),
                        args=status_args, method=URLRequest.PUT)
            except APIError, err:
                raise AlmException('Unable to update task status to DONE '
                                   'for card: %s in Trac because of %s' %
                                   (task.get_alm_id(),err))
        elif status== 'TODO':
            try:
                status_args = {
                    'card[properties][][name]':'status',
                    'card[properties][][value]': self.sde_plugin.config['trac_new_status']
                }
                self.alm_plugin.call_api('cards/%s.xml' % task.get_alm_id(),
                        args=status_args, method=URLRequest.PUT)
            except APIError, err:
                raise AlmException('Unable to update task status to TODO for '
                                   'card: %s in Trac because of %s' %
                                   (task.get_alm_id(), err))
        logger.debug('Status changed to %s for task %s in Trac' %
                (status, task.get_alm_id()))

    def alm_disconnect(self):
        pass
