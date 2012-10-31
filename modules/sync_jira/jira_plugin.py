# Copyright SDElements Inc
# Extensible two way integration with JIRA

from datetime import datetime

from sdelib.restclient import RESTBase, APIError
from alm_integration.alm_plugin_base import AlmTask, AlmConnector
from alm_integration.alm_plugin_base import AlmException
from sdelib.conf_mgr import Config

from sdelib import log_mgr
logger = log_mgr.mods.add_mod(__name__)

class JIRAAPIBase(RESTBase):
    """ Base plugin for JIRA """

    def __init__(self, config):
        super(JIRAAPIBase, self).__init__('alm', 'JIRA', config, 'rest/api/2')

class JIRATask(AlmTask):
    """ Representation of a task in JIRA """

    def __init__(self, task_id, alm_id, priority, status, resolution,
                 timestamp, done_statuses):
        self.task_id = task_id
        self.alm_id = alm_id
        self.priority = priority
        self.status = status
        self.resolution = resolution
        self.timestamp = timestamp
        self.done_statuses = done_statuses  # comma-separated list

    def get_task_id(self):
        return self.task_id

    def get_alm_id(self):
        return self.alm_id

    def get_priority(self):
        return self.priority

    def get_status(self):
        """ Translates JIRA priority into SDE priority """
        if self.status in self.done_statuses:
            return 'DONE'
        else:
            return 'TODO'

    def get_timestamp(self):
        """ Returns a datetime object """
        return datetime.strptime(self.timestamp.split('.')[0],
                                 '%Y-%m-%dT%H:%M:%S')

    @classmethod
    def translate_priority(cls, priority):
        """ Translates an SDE priority into a JIRA priority """
        try:
            priority = int(priority)
        except (TypeError):
            logger.error('Could not coerce %s into an integer' % priority)
            raise AlmException("Error in translating SDE priority to JIRA: "
                               "%s is not an integer priority" % priority)
        if priority == 10:
            return 'Blocker'
        elif 7 <= priority <= 9:
            return 'Critical'
        elif 5 <= priority <= 6:
            return 'Major'
        elif 3 <= priority <= 4:
            return 'Minor'
        else:
            return 'Trivial'

class JIRAConnector(AlmConnector):

    def __init__(self, config, alm_plugin):
        """ Initializes connection to JIRA """
        super(JIRAConnector, self).__init__(config, alm_plugin)

        config.add_custom_option('alm_standard_workflow', 'Standard workflow in JIRA?')
        config.add_custom_option('jira_issue_type', 'IDs for issues raised in JIRA')
        config.add_custom_option('jira_close_transition', 'Close transition in JIRA')
        config.add_custom_option('jira_reopen_transition', 'Re-open transiiton in JIRA')
        config.add_custom_option('jira_done_statuses', 'Done statuses in JIRA')

    def initialize(self):
        super(JIRAConnector, self).initialize()

        #Verify that the configuration options are set properly
        if (not self.sde_plugin.config['jira_done_statuses'] or
            len(self.sde_plugin.config['jira_done_statuses']) < 1):
            raise AlmException('Missing jira_done_statuses in configuration')

        self.sde_plugin.config['jira_done_statuses'] = (
                self.sde_plugin.config['jira_done_statuses'].split(','))

        if not self.sde_plugin.config['alm_standard_workflow']:
            raise AlmException('Missing alm_standard_workflow in configuration')
        if not self.sde_plugin.config['jira_issue_type']:
            raise AlmException('Missing jira_issue_type in configuration')
        if not self.sde_plugin.config['jira_close_transition']:
            raise AlmException('Missing jira_close_transition in configuration')
        if not self.sde_plugin.config['jira_reopen_transition']:
            raise AlmException('Missing jira_reopen_transition in configuration')

        self.close_transition_id = None
        self.reopen_transition_id = None
        self.jira_issue_type_id = None

    def alm_name(self):
        return "JIRA"

    def alm_connect(self):
        """ Verifies that JIRA connection works """
        #verify that we can connect to JIRA
        try:
            result = self.alm_plugin.call_api('project')
        except APIError:
            raise
            raise AlmException('Unable to connect to JIRA. Please' +
                               ' check server URL, ID, password')

        #verify that we can access project
        try:
            self.alm_plugin.call_api('project/%s' %
                                     (self.sde_plugin.config
                                     ['alm_project']))
        except APIError:
            raise AlmException('Unable to connect to JIRA project %s' %
                               (self.sde_plugin.config['alm_project']))

        #get Issue ID for given type name
        try:
            issue_types = self.alm_plugin.call_api('issuetype')
            for issue_type in issue_types:
                if (issue_type['name'] ==
                        self.sde_plugin.config['jira_issue_type']):
                    self.jira_issue_type_id = issue_type['id']
                    break
            if not self.jira_issue_type_id:
                raise AlmException('Issue type %s not available' %
                                   self.sde_plugin.config['jira_issue_type'])
        except APIError:
            raise AlmException('Unable to get issuetype from JIRA API')

    def alm_get_task (self, task):
        task_id = task['title'].partition(':')[0]
        result = None
        try:
            url = 'search?jql=project%%3D\'%s\'%%20AND%%20summary~\'%s\'' % (
                    self.sde_plugin.config['alm_project'], task_id)
            result = self.alm_plugin.call_api(url)
        except APIError, err:
            logger.info(err)
            raise AlmException("Unable to get task %s from JIRA" % task_id)
        if not result['total']:
            #No result was found from query
            return None
        #We will use the first result from the query
        jtask = result['issues'][0]
        resolution = None
        if jtask['fields']['resolution']:
            resolution = jtask['fields']['resolution']['name']
        return JIRATask(task['id'],
                        jtask['key'],
                        jtask['fields']['priority']['name'],
                        jtask['fields']['status']['name'],
                        resolution,
                        jtask['fields']['updated'],
                        self.sde_plugin.config['jira_done_statuses'])

    def alm_add_task(self, task):
        #Add task
        add_result = None
        args= {
           'fields': {
               'project': {
                   'key':self.sde_plugin.config['alm_project']
               },
               'summary':task['title'],
               'description':task['content'],
               'priority': {
                   'name':JIRATask.translate_priority(task['priority'])
               },
               'issuetype':{
                   'id': self.jira_issue_type_id
               }
           }
        }
        try:
            add_result = self.alm_plugin.call_api('issue',
                    method=self.alm_plugin.URLRequest.POST, args=args)
        except APIError:
            return None

        if (self.sde_plugin.config['alm_standard_workflow'] == 'True' and
            (task['status'] == 'DONE' or task['status'] == 'NA')):
            self.alm_update_task_status(self.alm_get_task(task), task['status'])

        #Return a unique identifier to this task in JIRA
        return 'Issue %s' % add_result['key']

    def alm_update_task_status(self, task, status):
        if (not task or
            not self.sde_plugin.config['alm_standard_workflow'] == 'True'):
            return

        trans_result = None
        trans_url = 'issue/%s/transitions' % task.get_alm_id()
        # TODO: these two block are nearly identical: refactor
        try:
            if status == 'DONE' or status == 'NA':
                if not self.close_transition_id:
                    transitions = self.alm_plugin.call_api(trans_url)
                    for transition in transitions['transitions']:
                        if transition['name'] == self.sde_plugin.config['jira_close_transition']:
                            self.close_transition_id = transition['id']
                            break
                    if not self.close_transition_id:
                        raise AlmException('Unable to find transition %s' %
                                self.sde_plugin.config['jira_close_transition'])
                trans_args = {'transition': {'id': self.close_transition_id}}
                trans_result = self.alm_plugin.call_api(trans_url, args=trans_args,
                        method=self.alm_plugin.URLRequest.POST)
            elif status=='TODO':
                #We are updating a closed task to TODO
                if not self.reopen_transition_id:
                    transitions = self.alm_plugin.call_api(trans_url)
                    for transition in transitions['transitions']:
                        if transition['name'] == self.sde_plugin.config['jira_reopen_transition']:
                            self.reopen_transition_id = transition['id']
                            break
                    if not self.reopen_transition_id:
                        raise AlmException('Unable to find transition %s' %
                                self.sde_plugin.config['jira_reopen_transition'])

                trans_args = {'transition': {'id':self.reopen_transition_id}}
                self.alm_plugin.call_api(trans_url, args=trans_args,
                        method=self.alm_plugin.URLRequest.POST)
        except self.alm_plugin.APIFormatError:
            # The response does not have JSON, so it is incorrectly raised as
            # a JSON formatting error. Ignore this error
            pass
        except APIError, err:
            raise AlmException("Unable to set task status: %s" % err)

    def alm_disconnect(self):
        pass
