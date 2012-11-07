# Copyright SDElements Inc
# Extensible two way integration with JIRA

from datetime import datetime

from alm_integration.alm_plugin_base import AlmConnector, AlmException
from modules.sync_jira.jira_shared import JIRATask
from sdelib.conf_mgr import Config

from sdelib import log_mgr
logger = log_mgr.mods.add_mod(__name__)

class JIRAConnector(AlmConnector):
    alm_name = 'JIRA'

    def __init__(self, config, alm_plugin):
        """ Initializes connection to JIRA """
        super(JIRAConnector, self).__init__(config, alm_plugin)

        config.add_custom_option('alm_standard_workflow', 'Standard workflow in JIRA?',
                default='True')
        config.add_custom_option('jira_issue_type', 'IDs for issues raised in JIRA',
                default='Bug')
        config.add_custom_option('jira_close_transition', 'Close transition in JIRA',
                default='Close Issue')
        config.add_custom_option('jira_reopen_transition', 'Re-open transiiton in JIRA',
                default='Reopen Issue')
        config.add_custom_option('jira_done_statuses', 'Statuses that signify a task is Done in JIRA',
                default='Resolved,Closed')

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

    def alm_connect(self):
        self.alm_plugin.connect()

        #get Issue ID for given type name
        issue_types = self.alm_plugin.get_issue_types()

        self.jira_issue_type_id = None
        for issue_type in issue_types:
            if (issue_type['name'] == self.config['jira_issue_type']):
                self.jira_issue_type_id = issue_type['id']
                break
        if self.jira_issue_type_id is None:
            raise AlmException('Issue type %s not available' % self.config['jira_issue_type'])

    def alm_get_task(self, task):
        task_id = task['title'].partition(':')[0]

        return self.alm_plugin.get_task(task, task_id)

    def alm_add_task(self, task):
        new_issue = self.alm_plugin.add_task(task)

        if (self.config['alm_standard_workflow'] == 'True' and
            (task['status'] == 'DONE' or task['status'] == 'NA')):
            self.alm_update_task_status(self.alm_get_task(task), task['status'])

        #Return a unique identifier to this task in JIRA
        return 'Issue %s' % new_issue['key']

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
