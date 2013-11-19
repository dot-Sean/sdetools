# Copyright SDElements Inc
# Extensible two way integration with GitHub

import re
import json
from datetime import datetime

from sdetools.sdelib.commons import urlencode_str
from sdetools.sdelib.restclient import RESTBase
from sdetools.sdelib.restclient import URLRequest, APIError
from sdetools.alm_integration.alm_plugin_base import AlmTask, AlmConnector
from sdetools.alm_integration.alm_plugin_base import AlmException

from sdetools.sdelib import log_mgr

logger = log_mgr.mods.add_mod(__name__)

RE_MAP_RANGE_KEY = re.compile('^\d+(-\d+)?$')
GITHUB_DEFAULT_PRIORITY_MAP = {
    '7-10': 'High',
    '4-6': 'Medium',
    '1-3': 'Low',
}
PUBLIC_TASK_CONTENT = 'Visit us at http://www.sdelements.com/ to find out how you can easily add project-specific '\
                      'software security requirements to your existing development processes.'
GITHUB_NEW_STATUS = 'open'
GITHUB_DONE_STATUS = 'closed'

class GitHubAPI(RESTBase):
    """ Base plugin for GitHub """

    def __init__(self, config):
        extra_conf_opts = [('alm_api_token', 'GitHub API Token', '')]
        super(GitHubAPI, self).__init__('alm', 'GitHub', config, extra_conf_opts=extra_conf_opts)

    def post_conf_init(self):
        if self._get_conf('api_token'):
            self.set_auth_mode('api_token')
            self.api_token_header_name = 'Authorization'
            self.config['alm_pass'] = 'token %s' % self._get_conf('api_token')

        super(GitHubAPI, self).post_conf_init()

    def parse_error(self, result):
        result = json.loads(result)
        error_msg = result.get('message')

        if not error_msg:
            logger.error('Could not parse error message')
            raise AlmException('Could not parse error message')

        errors = result.get('errors')

        if errors:
            additional_info = ''
            for error in errors:
                code = error['code']
                field = error['field']
                resource = error['resource']

                if code == 'missing':
                    additional_info += 'The resource "%s" does not exist.' % resource
                elif code == 'missing_field':
                    additional_info += 'The field "%s" is required for the resource "%s"' % (field, resource)
                elif code == 'invalid':
                    additional_info += 'The field "%s" is not properly formatted' % field
                elif code == 'already_exists':
                    additional_info += 'The value for the field "%s" already exists in another "%s" resource' % \
                                         (field, resource)
                else:
                    # Generic error formatting
                    additional_info += 'Resource: %s Code: %s Field: %s' % (resource, code, field)
            if additional_info:
                error_msg += '. Additional Info - %s' % additional_info
        return error_msg


class GitHubTask(AlmTask):
    """ Representation of a task in GitHub"""

    def __init__(self, task_id, alm_id, status, timestamp):
        self.task_id = task_id
        self.alm_id = alm_id
        self.status = status
        self.timestamp = timestamp
        self.priority = None

    def get_task_id(self):
        return self.task_id

    def get_alm_id(self):
        return self.alm_id

    def get_status(self):
        """ Translates GitHub status into SDE status """
        if self.status == GITHUB_DONE_STATUS:
            return 'DONE'
        else:
            return 'TODO'

    def get_timestamp(self):
        """ Returns a datetime object """
        return datetime.strptime(self.timestamp, '%Y-%m-%dT%H:%M:%SZ')


class GitHubConnector(AlmConnector):
    alm_name = 'GitHub'
    GITHUB_ISSUE_LABEL = 'github_issue_label'
    GITHUB_DUPLICATE_LABEL = 'github_duplicate_label'
    ALM_PROJECT_VERSION = 'alm_project_version'
    GITHUB_REPO_OWNER = 'github_repo_owner'
    ALM_PRIORITY_MAP = 'alm_priority_map'
    GITHUB_GROUP_LABEL = 'alm_group_label'

    def __init__(self, config, alm_plugin):
        """ Initializes connection to GitHub """
        super(GitHubConnector, self).__init__(config, alm_plugin)

        config.add_custom_option(self.GITHUB_ISSUE_LABEL, 'Issue type represented'
                                                          'by labels on GitHub', default='')
        config.add_custom_option(self.GITHUB_DUPLICATE_LABEL, 'GitHub label'
                                                              'for duplicate issues', default='duplicate')
        config.add_custom_option(self.ALM_PROJECT_VERSION, 'GitHub milestone',
                                 default='')
        config.add_custom_option(self.GITHUB_REPO_OWNER, 'GitHub repository owner', default=None)
        config.add_custom_option(self.ALM_PRIORITY_MAP, 'Customized map from priority in SDE to GITHUB '
                                                        '(JSON encoded dictionary of strings)', default='')
        config.add_custom_option(self.GITHUB_GROUP_LABEL, 'GitHub label for issues generated by SDElements',
                                 default='SD Elements')
        self.sync_titles_only = True

    def initialize(self):
        super(GitHubConnector, self).initialize()

        # Verify that the configuration options are set properly
        for item in [self.GITHUB_DUPLICATE_LABEL, self.GITHUB_REPO_OWNER]:
            if not self.config[item]:
                raise AlmException('Missing %s in configuration' % item)

        self.config.process_json_str_dict(self.ALM_PRIORITY_MAP)

        if not self.config[self.ALM_PRIORITY_MAP]:
            self.config[self.ALM_PRIORITY_MAP] = GITHUB_DEFAULT_PRIORITY_MAP

        for key in self.config[self.ALM_PRIORITY_MAP]:
            if not RE_MAP_RANGE_KEY.match(key):
                raise AlmException('Unable to process %s (not a JSON dictionary). Reason: Invalid range key %s'
                                   % (self.ALM_PRIORITY_MAP, key))

    def alm_connect_server(self):
        """ Verifies that GitHub connection works """
        # Check if user can successfully authenticate and retrieve user profile
        try:
            user_info = self.alm_plugin.call_api('user')
        except APIError, err:
            if self.config.get('alm_api_token'):
                auth_field_check = 'api token'
            else:
                auth_field_check = 'user, pass'
            raise AlmException('Unable to connect to GitHub service (Check server URL, %s). Reason: %s' %
                               (auth_field_check, str(err)))

    def alm_connect_project(self):
        """ Verifies that the GitHub repo exists """
        self.project_uri = '%s/%s' % (urlencode_str(self.config[self.GITHUB_REPO_OWNER]),
                                      urlencode_str(self.config['alm_project']))

        # Check if GitHub repo is accessible
        try:
            repo_info = self.alm_plugin.call_api('repos/%s' % self.project_uri)
        except APIError, err:
            raise AlmException('Unable to find GitHub repo. Reason: %s' % str(err))

        self.sync_titles_only = not repo_info.get('private')

        """ Validate project configurations """
        self.milestone_id = self.github_get_milestone_id(self.config[self.ALM_PROJECT_VERSION])

    def github_get_milestone_id(self, milestone_name):
        if not milestone_name:
            return None

        try:
            milestone_list = self.alm_plugin.call_api('repos/%s/milestones' % self.project_uri)
        except APIError, err:
            raise AlmException('Unable to get milestones from GitHub. Reason: %s' % str(err))

        for milestone in milestone_list:
            if milestone['title'] == milestone_name:
                return milestone['number']

        raise AlmException('Unable to find milestone %s from GitHub' % milestone_name)

    def alm_get_task(self, task):
        task_id = self._extract_task_id(task['id'])
        if not task_id:
            return None

        try:
            # We need to perform 2 API calls to search open and closed issues
            open_issues = self.alm_plugin.call_api('legacy/issues/search/%s/%s/%s:' %
                                                   (self.project_uri,
                                                    GITHUB_NEW_STATUS,
                                                    urlencode_str(task_id)))
            closed_issues = self.alm_plugin.call_api('legacy/issues/search/%s/%s/%s:' %
                                                     (self.project_uri,
                                                      GITHUB_DONE_STATUS,
                                                      urlencode_str(task_id)))
        except APIError, err:
            raise AlmException('Unable to get task %s from GitHub. Reason: %s' % (task_id, str(err)))

        issues_list = open_issues['issues']
        issues_list.extend(closed_issues['issues'])

        if not issues_list:
            return None

        index = 0

        # Prune list of issues labeled as duplicate
        while index < len(issues_list):
            issue = issues_list[index]
            duplicate_label = self.config[self.GITHUB_DUPLICATE_LABEL]

            if issue['labels'].count(duplicate_label) > 0:
                issues_list.pop(index)
            else:
                index += 1

        if len(issues_list) > 1:
            logger.warning('Found multiple issues with the title %s that are not labeled as duplicates.'
                           'Selecting the first task found with id %s' % (task_id, issues_list[0]['number']))
        elif not issues_list:
            return None

        logger.info('Found task: %s', task_id)
        return GitHubTask(task_id,
                          issues_list[0]['number'],
                          issues_list[0]['state'],
                          issues_list[0]['updated_at'])

    def translate_priority(self, priority):
        """ Translates an SDE priority into a GitHub label """
        pmap = self.config[self.ALM_PRIORITY_MAP]

        if not pmap:
            return None

        try:
            priority = int(priority)
        except TypeError:
            raise AlmException("Error in translating SDE priority to GitHub label: "
                               "%s is not an integer priority" % priority)

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

    def alm_add_task(self, task):
        github_priority_label = self.translate_priority(task['priority'])
        github_group_label = self.config[self.GITHUB_GROUP_LABEL]
        github_issue_label = self.config[self.GITHUB_ISSUE_LABEL]
        labels = []
        task_content = PUBLIC_TASK_CONTENT

        if not self.sync_titles_only:
            task_content = self.sde_get_task_content(task)

        create_args = {
            'title': task['title'],
            'body': task_content,
        }

        if github_priority_label:
            labels.append(github_priority_label)
        if github_group_label:
            labels.append(github_group_label)
        if github_issue_label:
            labels.append(github_issue_label)
        if labels:
            create_args['labels'] = labels
        if self.milestone_id:
            create_args['milestone'] = self.milestone_id

        try:
            new_issue = self.alm_plugin.call_api('repos/%s/issues' %
                                                 self.project_uri,
                                                 method=self.alm_plugin.URLRequest.POST,
                                                 args=create_args)
            logger.debug('Task %s added to GitHub Project', task['id'])
        except APIError, err:
            raise AlmException('Unable to add task %s to GitHub. Reason: %s'
                               % (task['id'], str(err)))

        # API returns JSON of the new issue
        alm_task = GitHubTask(task['id'],
                              new_issue['number'],
                              new_issue['state'],
                              new_issue['updated_at'])

        if self.config['alm_standard_workflow'] and (task['status'] == 'DONE' or task['status'] == 'NA'):
            self.alm_update_task_status(alm_task, task['status'])

        return 'Repository: %s, Issue: %s' % (self.config['alm_project'], alm_task.get_alm_id())

    def alm_update_task_status(self, task, status):
        if not task or not self.config['alm_standard_workflow']:
            logger.debug('Status synchronization disabled')
            return

        if status == 'DONE' or status == 'NA':
            alm_state = GITHUB_DONE_STATUS
        elif status == 'TODO':
            alm_state = GITHUB_NEW_STATUS
        else:
            raise AlmException('Unknown status %s' % status)

        update_args = {
            'state': alm_state
        }

        try:
            self.alm_plugin.call_api('repos/%s/issues/%s' % (self.project_uri, task.get_alm_id()),
                                              args=update_args, method=URLRequest.POST)
        except APIError, err:
            raise AlmException('Unable to update task status to %s for GitHub issue %s. Reason: %s' %
                               (status, task.get_alm_id(), str(err)))

        logger.debug('Status changed to %s for task %s in GitHub' % (status, task.get_alm_id()))

    def alm_disconnect(self):
        pass
