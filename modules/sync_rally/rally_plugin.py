# Copyright SDElements Inc
# Extensible two way integration with Rally

from datetime import datetime

from sdelib.restclient import RESTBase, APIError
from alm_integration.alm_plugin_base import AlmTask, AlmConnector
from alm_integration.alm_plugin_base import AlmException
from sdelib.conf_mgr import Config

from sdelib import log_mgr
logger = log_mgr.mods.add_mod(__name__)

API_VERSION = '1.11'

class RallyAPIBase(RESTBase):
    """ Base plugin for Rally """

    def __init__(self, config):
        super(RallyAPIBase, self).__init__('alm', 'ALM', config, 
                'slm/webservice/%s' % (API_VERSION))

class RallyTask(AlmTask):
    """ Representation of a task in Rally """

    def __init__(self, task_id, alm_id, alm_task_ref,
                 status, timestamp, done_statuses):
        self.task_id = task_id
        self.alm_id = alm_id

        #A Reference URL to the task in Rally
        self.alm_task_ref = alm_task_ref
        self.status = status
        self.timestamp = timestamp
        self.done_statuses = done_statuses #comma-separated list

    def get_task_id(self):
        return self.task_id

    def get_alm_task_ref(self):
        return self.alm_task_ref

    def get_alm_id(self):
        return self.alm_id

    def get_priority(self):
        return None

    def get_status(self):
        """Translates Rally status into SDE status"""
        return 'DONE' if self.status in self.done_statuses else 'TODO'

    def get_timestamp(self):
        """ Returns a datetime object """
        return datetime.strptime(self.timestamp, '%Y-%m-%dT%H:%M:%SZ')

class RallyConnector(AlmConnector):
    """Connects SD Elements to Rally"""

    def __init__(self, config, alm_plugin):
        super(RallyConnector, self).__init__(config, alm_plugin)

        """ Adds Rally specific config options to the config file"""
        config.add_custom_option('alm_standard_workflow', 'Standard workflow in Rally?',
            default='True')
        config.add_custom_option('rally_card_type', 'IDs for issues raised in Rally',
            default='Story')
        config.add_custom_option('rally_new_status', 'status to set for new tasks in Rally',
            default='Defined')
        config.add_custom_option('rally_done_statuses', 'Statuses that signify a task is Done in Rally',
            default='Completed,Accepted')
        config.add_custom_option('rally_workspace', 'Rally Workspace', default=None)

    def initialize(self):
        super(RallyConnector, self).initialize()

        #Verify that the configuration options are set properly
        for item in ['rally_done_statuses', 'alm_standard_workflow', 'rally_card_type',
            'rally_new_status', 'rally_workspace']:
            if not self.sde_plugin.config[item]:
                raise AlmException('Missing %s in configuration' % item)

        self.sde_plugin.config['rally_done_statuses'] = (
                self.sde_plugin.config['rally_done_statuses'].split(','))

        self.project_ref = None
        self.workspace_ref = None

    def carriage_return(self):
        return '<br//>'

    def alm_name(self):
        return 'Rally'

    def alm_connect(self):
        """ Verifies that Rally connection works """
        #Check to make sure that we can do a simple API call
        try:
            self.alm_plugin.call_api('task.js')
        except APIError:
            raise AlmException('Unable to connnect to Rally. Please check '
                               'server URL, ID, password, workspace and project')

        #Now try to get workspace ID
        try:
            query_args = {
                'query': '(Name = \"%s\")' % self.sde_plugin.config['rally_workspace']
            }
            workspace_ref = self.alm_plugin.call_api('workspace.js',
                                                       args=query_args)
            num_results = workspace_ref['QueryResult']['TotalResultCount']
            if not num_results:
                raise AlmException('Workspace is not valid, please check '
                                   'config value: '
                                   '%s' % self.sde_plugin.config['rally_workspace'])
            workspace_ref = workspace_ref['QueryResult']['Results'][0]['_ref']
            self.workspace_ref = workspace_ref

        except APIError:
            raise AlmException('Unable to connnect to Rally. Please check '
                               'server URL, ID, password and project')

        #Now get project ID
        try:
            query_args = {
                'query': '(Name = \"%s\")' % self.sde_plugin.config['alm_project']
            }
            project_ref = self.alm_plugin.call_api('project.js',
                                                    args = query_args)
            num_results = project_ref['QueryResult']['TotalResultCount']
            if not num_results:
                raise AlmException('Rally project is not valid, please check '
                                   'config value: %s' %
                                   self.sde_plugin.config['alm_project'])
            project_ref = project_ref['QueryResult']['Results'][0]['_ref']
            self.project_ref = project_ref

        except APIError:
            raise AlmException('Unable to connnect to Rally. Please '
                               'check server URL, ID, password and project')



    def alm_get_task (self, task):
        task_id = task['title']
        result = None

        try:
            query_args = {'query' : '(Name = \"%s\")' % task_id}
            result = self.alm_plugin.call_api('hierarchicalrequirement.js',
                                               args = query_args)
        except APIError as err:
            logger.info('Error is %s:' , err)
            raise AlmException('Unable to get task %s from Rally' % task_id)
        num_results = result['QueryResult']['TotalResultCount']

        if not num_results:
            return None

        try:
            task_result_url =  result['QueryResult']['Results'][0]['_ref']
            task_result_url = task_result_url.split('/%s/' % API_VERSION)[1]
            task_data = self.alm_plugin.call_api(task_result_url)
            task_data = task_data['HierarchicalRequirement']
            return RallyTask(task_id,
                             task_data['FormattedID'],
                             task_data['_ref'].split('/%s/' % API_VERSION)[1],
                             task_data['ScheduleState'],
                             task_data['LastUpdateDate'],
                             self.sde_plugin.config['rally_done_statuses'])
        except Exception as err:
            logger.info('Error is %s:', err)
            raise AlmException('Unable to get card # for task '
                               '%s from Rally' % task_id)

    def alm_add_task(self, task):
        try:
            if self.alm_get_task(task):
                logger.debug('Task %s already exists in Rally Project', task['id'])
                return None
        except AlmException:
            #This means task doesn't exist, which is expected
            pass
        try:
            create_args = { 
                'HierarchicalRequirement' : {
                    'Name': task['title'],
                    'Description': self.sde_get_task_content(task),
                    'Workspace': self.workspace_ref,
                    'Project': self.project_ref
                }
            }
            rsp = self.alm_plugin.call_api('hierarchicalrequirement/create.js',
                                            method = self.alm_plugin.URLRequest.POST,
                                            args = create_args)
            logger.info('Response was %s', rsp)
            logger.debug('Task %s added to Rally Project', task['id'])

        except APIError as err:
            raise AlmException('Please check ALM-specific settings in config '
                               'file. Unable to add task '
                               '%s because of %s' % (task['id'], err))

        #Return a unique identifier to this task in Rally
        logger.info('Getting task %s', task['id'])
        alm_task = self.alm_get_task(task)
        if not alm_task:
            raise AlmException('Alm task not added sucessfully. Please '
                               'check ALM-specific settings in config file')

        if (self.sde_plugin.config['alm_standard_workflow'] == 'True' and
            (task['status'] == 'DONE' or task['status'] == 'NA')):
            self.alm_update_task_status(alm_task, task['status'])

        return 'Project: %s, Story: %s' % (self.sde_plugin.config['alm_project'],
                                           alm_task.get_alm_id())


    def alm_update_task_status(self, task, status):

        if (not task or
            not self.sde_plugin.config['alm_standard_workflow'] == 'True'):
            logger.debug('Status synchronization disabled')
            return

        if status == 'DONE' or status == 'NA':
            try:
                trans_args = {
                        'HierarchicalRequirement' : {
                                'ScheduleState':
                                        self.sde_plugin.config['rally_done_statuses'][0]
                        }
                }
                self.alm_plugin.call_api(task.get_alm_task_ref(),
                                          args = trans_args,
                                          method=self.alm_plugin.URLRequest.POST)
            except APIError as err:
                raise AlmException('Unable to update task status to DONE '
                                   'for card: %s in Rally because of %s' % 
                                   (task.get_alm_id(), err))

        elif status == 'TODO':
            try:
                trans_args = {
                    'HierarchicalRequirement' : {
                        'ScheduleState': 
                            self.sde_plugin.config['rally_new_status']
                    }
                }
                self.alm_plugin.call_api(task.get_alm_task_ref(),
                                          args = trans_args,
                                          method=self.alm_plugin.URLRequest.POST)
            except APIError as err:
                raise AlmException('Unable to update task status to TODO '
                                   'for card: '
                                   '%s in Rally because of %s' %
                                   (task.get_alm_id(), err))

        logger.debug('Status changed to %s for task %s in Rally',
                      status, task.get_alm_id())

    def alm_disconnect(self):
        pass
