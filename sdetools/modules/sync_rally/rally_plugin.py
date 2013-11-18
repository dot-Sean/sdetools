# Copyright SDElements Inc
# Extensible two way integration with Rally

import sys
import re
from datetime import datetime

from sdetools.sdelib.restclient import RESTBase, APIError
from sdetools.alm_integration.alm_plugin_base import AlmTask, AlmConnector
from sdetools.alm_integration.alm_plugin_base import AlmException
from sdetools.sdelib.conf_mgr import Config
from sdetools.extlib import markdown

from sdetools.sdelib import log_mgr
logger = log_mgr.mods.add_mod(__name__)

API_VERSION = '1.39'

MAX_CONTENT_SIZE = 30000

RALLY_HEADERS = [
    ('X-RallyIntegrationName', 'SD Elements'),
    ('X-RallyIntegrationVendor', 'SD Elements'),
    ('X-RallyIntegrationVersion', '1.0'),
    ('X-RallyIntegrationOS', sys.platform),
    ('X-RallyIntegrationPlatform', 'Python %s' % sys.version.split(' ',1)[0].replace('\n', '')),
    ('X-RallyIntegrationLibrary', 'Rally REST API'),
]

RALLY_HTML_CONVERT = [
    ('<h1>', '<br><font size="5">'),
    ('<h2>', '<br><font size="4">'),
    ('<h3>', '<br><font size="3">'),
    ('<h4>', '<br><font size="2">'),
    ('<h5>', '<br><font size="2">'),
    ('<h6>', '<br><font size="2">'),
    (re.compile('</h[1-6]>'), '</font><br><br>'),
    ('<p>', ''),
    ('</p>', '<br><br>'),
    ('<pre><code>', '<span style="font-family: courier new,monospace;"><pre><code>'),
    ('</code></pre>', '</code></pre></span>'),
]

class RallyAPIBase(RESTBase):
    """ Base plugin for Rally """

    def __init__(self, config):
        super(RallyAPIBase, self).__init__('alm', 'Rally', config, 
                'slm/webservice/%s' % (API_VERSION))

    def get_custom_headers(self, target, method):
        return RALLY_HEADERS

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

    def get_status(self):
        """Translates Rally status into SDE status"""
        if self.status in self.done_statuses:
            return 'DONE'
        else:
            return 'TODO'

    def get_timestamp(self):
        """ Returns a datetime object """
        return datetime.strptime(self.timestamp, '%Y-%m-%dT%H:%M:%S.%fZ')

class RallyConnector(AlmConnector):
    """Connects SD Elements to Rally"""
    alm_name = 'Rally'

    def __init__(self, config, alm_plugin):
        super(RallyConnector, self).__init__(config, alm_plugin)

        """ Adds Rally specific config options to the config file"""
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
        for item in ['rally_done_statuses', 'rally_card_type', 'rally_new_status', 'rally_workspace']:
            if not self.config[item]:
                raise AlmException('Missing %s in configuration' % item)

        self.config.process_list_config('rally_done_statuses')

        self.project_ref = None
        self.workspace_ref = None

        self.mark_down_converter = markdown.Markdown(safe_mode="escape")

    def carriage_return(self):
        return '<br//>'

    def alm_connect_server(self):
        """ Verifies that Rally connection works """
        #Check to make sure that we can do a simple API call
        try:
            self.alm_plugin.call_api('task.js')
        except APIError, err:
            raise AlmException('Unable to connect to Rally service (Check server URL, '
                    'user, pass). Reason: %s' % str(err))

    def alm_connect_project(self):
        workspace_ref = None

        #Now try to get workspace ID
        try:
            subscription_ref = self.alm_plugin.call_api('subscription.js')
        except APIError, err:
            raise AlmException('Unable to retrieve subscription from Rally. Reason: %s' % err)

        for workspace in subscription_ref['Subscription']['Workspaces']:
            if workspace['_refObjectName'] == self.config['rally_workspace']:
                workspace_ref = workspace['_ref']
                break

        if not workspace_ref:
            raise AlmException('Workspace is not valid, please check config value: '
                    '%s' % self.config['rally_workspace'])
        self.workspace_ref = workspace_ref

        #Now get project ID
        query_args = {
            'query': '(Name = \"%s\")' % self.config['alm_project'],
            'workspace': self.workspace_ref,
        }
        project_ref = self.alm_plugin.call_api('project.js',
                                                args = query_args)
        num_results = project_ref['QueryResult']['TotalResultCount']
        if not num_results:
            raise AlmException('Rally project not found: %s' % self.config['alm_project'])
        project_ref = project_ref['QueryResult']['Results'][0]['_ref']
        self.project_ref = project_ref

        self.validate_configs()

    def validate_configs(self):
        try:
            print self.alm_plugin.call_api('typedefinition?query=(Name = Defect)&fetch=true')
        except APIError, err:
            raise AlmException('Error retrieving thigns')

    def alm_get_task(self, task):
        task_id = self._extract_task_id(task['id'])
        query_args = {
            'query': '(Name contains \"%s:\")' % task_id,
            'workspace': self.workspace_ref,
            'project': self.project_ref,
        }

        try:
            result = self.alm_plugin.call_api('hierarchicalrequirement.js',args=query_args)
        except APIError, err:
            raise AlmException('Unable to get task %s from Rally. Reason: %s' % (task_id, str(err)))
        num_results = result['QueryResult']['TotalResultCount']

        if not num_results:
            return None

        task_result_url = result['QueryResult']['Results'][0]['_ref']
        task_result_url = task_result_url.split('/%s/' % API_VERSION)[1]
        try:
            task_data = self.alm_plugin.call_api(task_result_url)
        except APIError, err:
            raise AlmException('Unable to get card # for task %s from Rally. Reason: %s' % (task_id, str(err)))
        task_data = task_data['HierarchicalRequirement']

        return RallyTask(task_id,
                         task_data['FormattedID'],
                         task_data['_ref'].split('/%s/' % API_VERSION)[1],
                         task_data['ScheduleState'],
                         task_data['LastUpdateDate'],
                         self.config['rally_done_statuses'])

    def alm_add_task(self, task):
        try:
            create_args = { 
                'HierarchicalRequirement' : {
                    'Name': task['title'],
                    'Description': self.sde_get_task_content(task),
                    'Workspace': self.workspace_ref,
                    'Project': self.project_ref
                }
            }
            result = self.alm_plugin.call_api('hierarchicalrequirement/create.js',
                    method = self.alm_plugin.URLRequest.POST, args = create_args)
            logger.debug('Task %s added to Rally Project', task['id'])

        except APIError, err:
            raise AlmException('Unable to add task to Rally %s because of %s' % 
                    (task['id'], err))
        if result['CreateResult']['Errors']:
            raise AlmException('Unable to add task to Rally %s. Reason: %s' % 
                    (task['id'], str(result['CreateResult']['Errors'])[:200]))

        #Return a unique identifier to this task in Rally
        logger.info('Getting task %s', task['id'])
        alm_task = self.alm_get_task(task)
        if not alm_task:
            raise AlmException('Alm task not added sucessfully. Please '
                               'check ALM-specific settings in config file')

        if (self.config['alm_standard_workflow'] and
            (task['status'] == 'DONE' or task['status'] == 'NA')):
            self.alm_update_task_status(alm_task, task['status'])

        return 'Project: %s, Story: %s' % (self.config['alm_project'],
                                           alm_task.get_alm_id())


    def alm_update_task_status(self, task, status):
        if not task or not self.config['alm_standard_workflow']:
            logger.debug('Status synchronization disabled')
            return
        if status == 'DONE' or status == 'NA':
            schedule_state = self.config['rally_done_statuses'][0]
            status = 'DONE'
        elif status == 'TODO':
            schedule_state = self.config['rally_new_status']
        else:
            raise AlmException('Invalid status %s' % status)

        trans_args = {
            'HierarchicalRequirement': {
                'ScheduleState': schedule_state
            }
        }

        try:
            self.alm_plugin.call_api(task.get_alm_task_ref(), args=trans_args, method=self.alm_plugin.URLRequest.POST)
        except APIError, err:
            raise AlmException('Unable to update task status to %s for card: %s in Rally because of %s' %
                               (status, task.get_alm_id(), err))

        logger.debug('Status changed to %s for task %s in Rally' % (status, task.get_alm_id()))

    def alm_disconnect(self):
        pass

    def convert_markdown_to_alm(self, content, ref): 
        s = self.mark_down_converter.convert(content)

        # We do some jumping through hoops to add <br> at end of each
        # line for segments between code tags
        sliced = s.split('<code>')
        s = [sliced[0]]
        for item in sliced[1:]:
            item = item.split('</code>')
            item[0] = item[0].replace('\n', '<br>\n')
            s.append('</code>'.join(item))
        s = '<code>'.join(s)

        for before, after in RALLY_HTML_CONVERT:
            if type(before) is str:
                s = s.replace(before, after)
            else:
                s = before.sub(after, s)

        if len(s) > MAX_CONTENT_SIZE:
            logger.warning('Content too long for %s - Truncating.' % ref)
            s = s[:MAX_CONTENT_SIZE]

        return s

