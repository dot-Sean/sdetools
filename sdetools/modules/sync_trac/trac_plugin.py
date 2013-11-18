# Copyright SDElements Inc
# Extensible two way integration with Trac

import xmlrpclib
import socket
from datetime import datetime

from sdetools.sdelib.commons import UsageError, json, urlencode_str
from sdetools.sdelib.restclient import RESTBase
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
            urlencode_str(self._get_conf('user')),
            urlencode_str(self._get_conf('pass')),
            self.server, 
            self.base_path)

    def connect(self):
        if self.proxy:
            return
        self.post_conf_init()
        self.proxy = xmlrpclib.ServerProxy(self.base_uri)

class TracTask(AlmTask):
    """ Representation of a task in Trac"""

    def __init__(self, task_id, alm_id, status, timestamp, done_statuses, milestone):
        self.task_id = task_id
        self.alm_id = alm_id
        self.status = status
        self.timestamp = timestamp
        self.done_statuses = done_statuses  # comma-separated list
        self.milestone = milestone

    def get_task_id(self):
        return self.task_id

    def get_alm_id(self):
        return self.alm_id

    def get_milestone(self):
        return self.milestone

    def get_status(self):
        """ Translates Trac status into SDE status """
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

        config.add_custom_option('alm_close_transition', 'Close transition in Trac',
                default='resolve,{"action_resolve_resolve_resolution":"fixed"}')
        config.add_custom_option('alm_reopen_transition', 'Re-open transiiton in Trac',
                default='reopen')
        config.add_custom_option('alm_new_status', 'Status to set for new tasks in Trac',
            default='Ready for Analysis')
        config.add_custom_option('alm_done_statuses', 'Statuses that signify a task is Done in Trac',
            default='closed')
        self.alm_task_title_prefix = 'SDE '

    def initialize(self):
        super(TracConnector, self).initialize()

        #Verify that the configuration options are set properly
        self.config.process_list_config('alm_done_statuses')

        if (not self.config['alm_done_statuses'] or
            len(self.config['alm_done_statuses']) < 1):
            raise UsageError('Missing alm_done_statuses in configuration')

        for action_type in ['alm_close_transition', 'alm_reopen_transition']:
            action_to_take = self.config[action_type]

            if not action_to_take:
                raise UsageError('Missing %s value' % action_type)

            if ',' in action_to_take:
                action_to_take, action_args = action_to_take.split(',', 1)
            else:
                action_args = '{}'
            try:
                action_args = json.loads(action_args)
            except:
                raise UsageError('Unable to JSON decode action arguments: %s' % action_args)
            if type(action_args) is not dict:
                raise UsageError('Invalid action argument: %s' % repr(action_args))
            self.config[action_type] = (action_to_take, action_args)
            

    def alm_connect_server(self):
        """ Perform initial connect and verify that Trac connection works """
        try:
            self.alm_plugin.connect()
            api_version = self.alm_plugin.proxy.system.getAPIVersion()
        except socket.error, err:
            raise AlmException('Unable to connect to Trac server (check the server URL) '
                    'Reason: %s' % (str(err)))
        except (xmlrpclib.ProtocolError, xmlrpclib.Fault), err:
            if hasattr(err, 'url'):
                err.url = err.url.split('@', 1)[-1]
            raise AlmException('Unable to connect to Trac XML-RPC. Please verify '
                    'the server URL, username, and password. Reason: %s' % (str(err)))
        except Exception, err:
            raise AlmException('Unknown error when attempting to connect '
                    ' to trac: %s' % (str(err)))

        trac_ver = '?'
        if(api_version[0] == 0):
            trac_ver = '0.10'
        elif (api_version[0] == 1):
            trac_ver = '0.11 or higher'
        print api_version
        logger.debug('Connected to Trac API %s v%s.%s' % (trac_ver, api_version[1], api_version[2]))

    def alm_connect_project(self):
        #TODO: Check milestone if present
        pass

    def _vet_alm_tasks(self, tasks):
        if len(tasks) > 1:
            logger.warning('More than one task matched search ...')
        return tasks[0]

    def _get_trac_task_by_id(self, sde_id, alm_id):
        trac_task = self.alm_plugin.proxy.ticket.get(alm_id)
        print trac_task[3]
        return TracTask(sde_id, alm_id, trac_task[3]['status'], trac_task[3]['changetime'],
                          self.config['alm_done_statuses'], trac_task[3]['milestone'])

    def alm_get_task(self, task):
        sde_id = self._extract_task_id(task['id'])

        # The colon is needed, otherwise for "T6" we match on "T6" and "T68"
        qstr = 'summary^=%s%s:' % (self.alm_task_title_prefix, sde_id)
        task_list = self.alm_plugin.proxy.ticket.query(qstr)
        if not task_list:
            return None

        alm_id = self._vet_alm_tasks(task_list)

        trac_ticket = self._get_trac_task_by_id(sde_id, alm_id)

        # Option A - Re-use the same ticket across milestones
        if trac_ticket.get_milestone() != self.config['alm_project']:
            self.alm_update_task_milestone(trac_ticket, self.config['alm_project'])
            return self.alm_get_task(task)

        return trac_ticket

    def alm_add_task(self, task):
        sde_id = self._extract_task_id(task['id'])
        title = '%s%s' % (self.alm_task_title_prefix, task['title'])

        alm_id = self.alm_plugin.proxy.ticket.create(
            title,
            self.sde_get_task_content(task),
            {
                'status': self.config['alm_new_status'],
                'milestone': self.config['alm_project']
            })

        if not alm_id:
            raise AlmException('Alm task not added sucessfully. Please '
                               'check ALM-specific settings in config file')

        alm_task = self._get_trac_task_by_id(sde_id, alm_id)

        if (self.config['alm_standard_workflow'] and
                (task['status']=='DONE' or task['status']=='NA')):
            self.alm_update_task_status(alm_task, task['status'])
        return 'Milestone: %s, Ticket: %s' % (self.config['alm_project'], alm_id)

    def alm_update_task_milestone(self, task, milestone):
        comment = 'Syncing: Task %s assigned to milestone %s via SD Elements' % (task.task_id, milestone)

        update_args = {
            'milestone': self.config['alm_project']
            }

        task_list = self.alm_plugin.proxy.ticket.update(task.get_alm_id(),
                comment, update_args)
        if not task_list:
            logger.error('Update failed for %s' % task.task_id)
            return None

        logger.debug('Milestone changed to %s for ticket %s in Trac' %
                (milestone, task.get_alm_id()))

        self.alm_update_task_status(task, "TODO")
    
    def alm_update_task_status(self, task, status):
        if not task or not self.config['alm_standard_workflow']:
            logger.debug('Status synchronization disabled')
            return

        # We have the required status; do not update
        if task.get_status() == status:
            return

        comment = 'Syncing: Task %s set %s in SD Elements' % (task.task_id, status)

        action_set = self.alm_plugin.proxy.ticket.getActions(task.get_alm_id())

        if status == 'DONE' or status=='NA':
            action_to_take, action_args = self.config['alm_close_transition']
        elif status == 'TODO':
            action_to_take, action_args = self.config['alm_reopen_transition']
        else:
            raise AlmException('Invalid SD Elements state: %s' % (status))

        action = None
        for entry in action_set:
            if entry[0] == action_to_take:
                action = action_to_take
                break
        if not action:
            logger.error('Unable to find a matching available action for updating %s to %s' %
                (task.task_id, status))
            return

        update_args = {
            'action': action,
            'milestone': self.config['alm_project']
            }
        update_args.update(action_args)

        task_list = self.alm_plugin.proxy.ticket.update(task.get_alm_id(),
                comment, update_args)
        if not task_list:
            logger.error('Update failed for %s' % task.task_id)
            return None

        logger.debug('Status changed to %s for ticket %s in Trac' %
                (status, task.get_alm_id()))

    def alm_disconnect(self):
        pass
