# Copyright SDElements Inc
# Extensible two way integration with JIRA

import re
from datetime import datetime

from sdetools.alm_integration.alm_plugin_base import AlmConnector, AlmException
from sdetools.modules.sync_jira.jira_rest import JIRARestAPI
from sdetools.modules.sync_jira.jira_markdown import convert_markdown
from sdetools.sdelib.conf_mgr import Config

from sdetools.sdelib import log_mgr
logger = log_mgr.mods.add_mod(__name__)

RE_MAP_RANGE_KEY = re.compile('^\d+(-\d+)?$')
JIRA_DEFAULT_PRIORITY_MAP = {
    '10': 'Blocker',
    '7-9': 'Critical',
    '5-6': 'Major',
    '3-4': 'Minor',
    '1-2': 'Trivial',
    }

class JIRAConnector(AlmConnector):
    alm_name = 'JIRA'

    def __init__(self, config, alm_plugin):
        """ Initializes connection to JIRA """
        super(JIRAConnector, self).__init__(config, alm_plugin)

        config.add_custom_option('jira_issue_type', 'IDs for issues raised in JIRA',
                default='Bug')
        config.add_custom_option('jira_close_transition', 'Close transition in JIRA',
                default='Close Issue')
        config.add_custom_option('jira_reopen_transition', 'Re-open transition in JIRA',
                default='Reopen Issue')
        config.add_custom_option('jira_done_statuses', 'Statuses that signify a task is Done in JIRA',
                default='Resolved,Closed')
        config.add_custom_option('jira_existing_issue', 'Provide the key of an existing issue to support custom fields (JIRA 4.x only)',
                default='')
        config.add_custom_option('alm_project_version', 'Project version',
                default='')
        config.add_custom_option('alm_parent_issue', 'Create sub-tasks under this issue',
                default='')
        config.add_custom_option('alm_priority_map', 'Customized map from priority in SDE to JIRA '
                '(JSON encoded dictionary of strings)',
                default='')

    def initialize(self):
        super(JIRAConnector, self).initialize()

        #Verify that the configuration options are set properly
        if (not self.config['jira_done_statuses'] or
            len(self.config['jira_done_statuses']) < 1):
            raise AlmException('Missing jira_done_statuses in configuration')

        self.config['jira_done_statuses'] = (self.config['jira_done_statuses'].split(','))

        if not self.config['jira_issue_type']:
            raise AlmException('Missing jira_issue_type in configuration')
        if not self.config['jira_close_transition']:
            raise AlmException('Missing jira_close_transition in configuration')
        if not self.config['jira_reopen_transition']:
            raise AlmException('Missing jira_reopen_transition in configuration')

        self.config.process_json_str_dict('alm_priority_map')
        if not self.config['alm_priority_map']:
            self.config['alm_priority_map'] = JIRA_DEFAULT_PRIORITY_MAP
        for key in self.config['alm_priority_map']:
            if not RE_MAP_RANGE_KEY.match(key):
                raise AlmException('Unable to process alm_priority_map (not a JSON dictionary). '
                        'Reason: Invalid range key %s' % key)

        if self.config['alm_custom_fields'] and self.config.jira_api_ver == 4 and not self.config['jira_existing_issue']:
            raise AlmException('Unable to process alm_custom_fields. '
                    'Reason: jira_existing_issue must be specified')
        
        self.transition_id = {
            'close': None,
            'reopen': None}

    def alm_connect_server(self):
        self.alm_plugin.connect_server()

        #get Issue ID for given type name
        if self.config['alm_parent_issue']:
            issue_types = self.alm_plugin.get_subtask_issue_types()
        else:
            issue_types = self.alm_plugin.get_issue_types()
        
        self.jira_issue_type_id = None
        for issue_type in issue_types:
            if (issue_type['name'] == self.config['jira_issue_type']):
                self.jira_issue_type_id = issue_type['id']
                break
        if self.jira_issue_type_id is None:
            raise AlmException('Issue type %s not available' % self.config['jira_issue_type'])

    def alm_connect_project():
        self.alm_plugin.connect_project()

        self.project_version = self.alm_get_version(self.config['alm_project_version'])
        if self.config['alm_project_version'] and not self.project_version:
            raise AlmException('Version %s not found in the project' % (self.config['alm_project_version']))

        self.custom_fields = []
        if self.config['alm_custom_fields']:
            fields = self.alm_plugin.get_fields()
            for key in self.config['alm_custom_fields']:
                for field in fields:
                    if (key == field['name']):
                        self.custom_fields.append({'field': field['id'],'value':self.config['alm_custom_fields'][key]})

            if len(self.custom_fields) != len(self.config['alm_custom_fields']):
                raise AlmException('At least one custom fields could not be found')

    def alm_get_task(self, task):
        task_id = task['title'].partition(':')[0]

        task = self.alm_plugin.get_task(task, task_id)
        if task:
            # Assign a project version
            if self.config['alm_project_version'] and not (self.config['alm_project_version'] in task.versions):
                # new version needed, re-open it and add it
                self.alm_update_task_status(task, "TODO")
                self.alm_set_version(task, self.config['alm_project_version'])
            
        return task

    def alm_add_task(self, task):
        task['formatted_content'] = self.sde_get_task_content(task)
        task['alm_priority'] = self.translate_priority(task['priority'])

        new_issue = self.alm_plugin.add_task(task, self.jira_issue_type_id, self.project_version, self.custom_fields)
        logger.info('Create new task in JIRA: %s' % new_issue['key'])

        if (self.config['alm_standard_workflow'] and
            (task['status'] == 'DONE' or task['status'] == 'NA')):
            alm_task = self.alm_get_task(task)
            self.alm_update_task_status(alm_task, task['status'])

        #Return a unique identifier to this task in JIRA
        return 'Issue %s' % new_issue['key']

    def alm_update_task_status(self, task, status):
        if not task or not self.config['alm_standard_workflow']:
            return

        alm_id = task.get_alm_id()

        # This is an unexpected situation
        if (task.get_status() == status):
            logger.debug('Status update in JIRA not required for issue %s' % alm_id)
            return

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

    def alm_get_version(self, version_name):
        for v in self.alm_plugin.versions:
            if v['name']==version_name:
                return v
        return None
 
    def alm_set_version(self, task, version):
        if not version:
            return False

        if version in task.versions:
            return False

        # validate that the project version exists
        jira_version = self.alm_get_version(version)
        if not jira_version:
            raise AlmException("Version %s could not be found in JIRA. '\
                    'Check your sync settings or add the version to JIRA" % version)

        # For SOAP, we must assign all versions (including the new one) to the task
        task.versions.append(version)

        self.alm_plugin.set_version(task, version)

        return True

    def alm_disconnect(self):
        pass

    def convert_markdown_to_alm(self, content, ref): 
        return convert_markdown(content)

    def translate_priority(self, priority):
        """ Translates an SDE priority into a JIRA priority """
        try:
            priority = int(priority)
        except (TypeError):
            logger.error('Could not coerce %s into an integer' % priority)
            raise AlmException("Error in translating SDE priority to JIRA: "
                               "%s is not an integer priority" % priority)
        pmap = self.config['alm_priority_map']
        for key in pmap:
            if '-' in key:
                lrange, hrange = key.split('-')
                lrange = int(lrange)
                hrange = int(hrange)
                if lrange <= priority <= hrange:
                    return pmap[key]
            else:
                if int(key) == priority:
                    return pmap[key]
