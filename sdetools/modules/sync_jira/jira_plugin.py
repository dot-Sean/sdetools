# Copyright SDElements Inc
# Extensible two way integration with JIRA

from datetime import datetime

from alm_integration.alm_plugin_base import AlmConnector, AlmException
from modules.sync_jira.jira_shared import JIRATask
from modules.sync_jira.jira_rest import JIRARestAPI
from modules.sync_jira.jira_markdown import convert_markdown
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
        if (not self.config['jira_done_statuses'] or
            len(self.config['jira_done_statuses']) < 1):
            raise AlmException('Missing jira_done_statuses in configuration')

        self.config['jira_done_statuses'] = (self.config['jira_done_statuses'].split(','))

        if not self.config['alm_standard_workflow']:
            raise AlmException('Missing alm_standard_workflow in configuration')
        if not self.config['jira_issue_type']:
            raise AlmException('Missing jira_issue_type in configuration')
        if not self.config['jira_close_transition']:
            raise AlmException('Missing jira_close_transition in configuration')
        if not self.config['jira_reopen_transition']:
            raise AlmException('Missing jira_reopen_transition in configuration')

        self.transition_id = {
            'close': None,
            'reopen': None}

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
        task['formatted_content'] = self.sde_get_task_content(task)

        new_issue = self.alm_plugin.add_task(task, self.jira_issue_type_id)
        logger.info('Create new task in JIRA: %s' % new_issue['key'])

        if (self.config['alm_standard_workflow'] == 'True' and
            (task['status'] == 'DONE' or task['status'] == 'NA')):
            alm_task = self.alm_get_task(task)
            self.alm_update_task_status(alm_task, task['status'])

        #Return a unique identifier to this task in JIRA
        return 'Issue %s' % new_issue['key']

    def alm_update_task_status(self, task, status):
        if (not task or
            not self.config['alm_standard_workflow'] == 'True'):
            return
        
        alm_id = task.get_alm_id()

        trans_table = self.alm_plugin.get_available_transitions(alm_id)

        if status == 'DONE' or status == 'NA':
            new_state = 'close'
        elif status == 'TODO':
            new_state = 'reopen'

        trans_name = self.config['jira_%s_transition' % new_state]
        if trans_name not in trans_table:
            raise AlmException('Unable to find transition %s' % trans_name)
        trans_id = trans_table[trans_name]

        self.alm_plugin.update_task_status(alm_id, trans_id)

        logger.info('Updated task status in JIRA for task %s' % alm_id)

    def alm_disconnect(self):
        pass

    def convert_markdown_to_alm(self, content, ref): 
        return convert_markdown(content)
