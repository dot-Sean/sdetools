# Copyright SDElements Inc
# Extensible two way integration with Rally

import sys, os

sys.path.append(os.path.split(os.path.split(os.path.abspath(__file__))[0])[0])
from sdelib.apiclient import APIBase, URLRequest, APIError
from alm_integration.alm_plugin_base import AlmTask, AlmConnector
from alm_integration.alm_plugin_base import AlmException, add_alm_config_options
from sdelib.conf_mgr import Config
from datetime import datetime
import logging
import copy

API_VERSION = '1.11'

class RallyAPIBase(APIBase):
    """ Base plugin for Mingle """

    def __init__(self, config):
        #Workaround to copy over the ALM id & password for Mingle
        #authentication without overwriting the SD Elements
        #email & password in the config
        alm_config = copy.deepcopy(config)
        alm_config['email'] = alm_config['alm_id']
        alm_config['password'] = alm_config['alm_password']
        super(RallyAPIBase, self).__init__(alm_config)
        self.base_uri = '%s://%s/slm/webservice/%s' % ((self.config['alm_method'],
                                                        self.config['alm_server'],
                                                        API_VERSION))

class RallyConfig(Config):
    """Configuration for Rally"""

    def set_settings(self, config):
        self.settings = config.copy()

class RallyTask(AlmTask):
    """ Representation of a task in Rally """

    def __init__(self, task_id, alm_id, alm_task_ref,
                 status, timestamp, done_statuses):
        self.task_id = task_id
        self.alm_id = alm_id

        #A Reference URL to the task in Mingle
        self.alm_task_ref = alm_task_ref
        self.status = status
        self.timestamp = timestamp
        self.done_statuses = done_statuses
        self.carriage_return = '<br/>' #comma-separated list

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
        return datetime.strptime(self.timestamp,
                                 '%Y-%m-%dT%H:%M:%SZ')

class RallyConnector(AlmConnector):
    """Connects SD Elements to Rally"""

    def __init__(self, sde_plugin, alm_plugin):
        """ Initializes connection to Rally """
        super(RallyConnector, self).__init__(sde_plugin, alm_plugin)

        #Verify that the configuration options are set properly
        if (not self.sde_plugin.config['rally_done_statuses'] or
            len(self.sde_plugin.config['rally_done_statuses']) < 1):
            raise AlmException('Missing rally_done_statuses in configuration')

        self.sde_plugin.config['rally_done_statuses'] = (
                self.sde_plugin.config['rally_done_statuses'].split(','))

        if not self.sde_plugin.config['alm_standard_workflow']:
            raise AlmException('Missing alm_standard_workflow in configuration')

        if not self.sde_plugin.config['rally_card_type']:
            raise AlmException('Missing rally_card_type in configuration')

        if not self.sde_plugin.config['rally_new_status']:
            raise AlmException('Missing rally_card_type in configuration')

        if not self.sde_plugin.config['rally_workspace']:
            raise AlmException('Missing rally_workspace in configuration')

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
            self.alm_plugin._call_api('task.js')
        except APIError:
            raise AlmException('Unable to connnect to Rally. Please check '
                               'server URL, ID, password, workspace and project')

        #Now try to get workspace ID
        try:
            query_args = {
                'query' : '(Name = \"%s\")' % self.sde_plugin.config['rally_workspace']
            }
            workspace_ref = self.alm_plugin._call_api('workspace.js',
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
                'query' : '(Name = \"%s\")' % self.sde_plugin.config['alm_project']
            }
            project_ref = self.alm_plugin._call_api('project.js',
                                                    args = query_args)
            num_results = project_ref['QueryResult']['TotalResultCount']
            if not num_results:
                raise AlmException('Rally project is not valid, please check'
                                   'config value:'
                                   '%s' % self.sde_plugin.config['alm_project'])
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
            result = self.alm_plugin._call_api('hierarchicalrequirement.js',
                                               args = query_args)
        except APIError as err:
            logging.info('Error is %s:' , err)
            raise AlmException('Unable to get task %s from Rally' % task_id)
        num_results = result['QueryResult']['TotalResultCount']

        if not num_results:
            return None

        try:
            task_result_url =  result['QueryResult']['Results'][0]['_ref']
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
            logging.info('Error is %s:', err)
            raise AlmException('Unable to get card # for task '
                               '%s from Rally' % task_id)

    def alm_add_task(self, task):
        try:
            if self.alm_get_task(task):
                logging.debug('Task %s already exists in Rally Project', task['id'])
                return None
        except AlmException:
            #This means task doesn't exist, which is expected
            pass
        try:
            create_args = { 'HierarchicalRequirement' :
                                {'Name':task['title'],
                                 'Description': self.sde_get_task_content(task),
                                 'Workspace': self.workspace_ref,
                                 'Project': self.project_ref
                                }
                          }
            rsp = self.alm_plugin._call_api('hierarchicalrequirement/create.js',
                                       method=URLRequest.POST,
                                       args = create_args)
            logging.info('Response was %s', rsp)
            logging.debug('Task %s added to Rally Project', task['id'])

        except APIError as err:
            raise AlmException('Please check ALM-specific settings in config '
                               'file. Unable to add task '
                               '%s because of %s' % (task['id'], err))

        #Return a unique identifier to this task in Rally
        logging.info('Getting task %s', task['id'])
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
            logging.debug('Status synchronization disabled')
            return

        if status == 'DONE' or status == 'NA':
            try:
                trans_args = {'HierarchicalRequirement' :
                                {'ScheduleState':
                                    self.sde_plugin.config['rally_done_statuses'][0]
                                }
                             }
                self.alm_plugin._call_api(task.get_alm_task_ref(),
                                          args = trans_args,
                                          method=URLRequest.POST)
            except APIError as err:
                raise AlmException('Unable to update task status to DONE '
                                   'for card: '
                                   '%s in Rally because of %s' % (
                                        task.get_alm_id(), err)
                                   )

        elif status == 'TODO':
            try:
                trans_args = {'HierarchicalRequirement' :
                                {'ScheduleState':
                                    self.sde_plugin.config['rally_new_status']
                                }
                             }
                self.alm_plugin._call_api(task.get_alm_task_ref(),
                                          args = trans_args,
                                          method=URLRequest.POST)
            except APIError as err:
                raise AlmException('Unable to update task status to TODO '
                                   'for card: '
                                   '%s in Rally because of %s' %
                                   (task.get_alm_id(), err))

        logging.debug('Status changed to %s for task %s in Rally',
                      status, task.get_alm_id())

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
