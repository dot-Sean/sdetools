# Copyright SDElements Inc
# Extensible two way integration with GitHub

import urllib
from datetime import datetime

from sdetools.extlib import http_req
from sdetools.sdelib.commons import urlencode_str
from sdetools.sdelib.restclient import RESTBase
from sdetools.sdelib.restclient import URLRequest, APIError
from sdetools.alm_integration.alm_plugin_base import AlmTask, AlmConnector
from sdetools.alm_integration.alm_plugin_base import AlmException
from sdetools.sdelib.conf_mgr import Config

from sdetools.sdelib import log_mgr
logger = log_mgr.mods.add_mod(__name__)

class GitHubAPI(RESTBase):
    """ Base plugin for GitHub """

    def __init__(self, config):
        super(GitHubAPI, self).__init__('alm', 'GitHub', config, '')
        self.proxy = None
        
    def post_conf_init(self):
        urllib_debuglevel = 0
        if __name__ in self.config['debug_mods']:
            urllib_debuglevel = 1

        self.opener = http_req.get_opener(
            self._get_conf('method'),
            self._get_conf('server'),
            debuglevel=urllib_debuglevel)
        self.config['%s_server' % (self.conf_prefix)] = self.opener.server

        self.session_info = None
        self.server = self._get_conf('server') 
        self.base_uri = '%s://%s' % (self._get_conf('method'), self.server)
           
class GitHubTask(AlmTask):
    """ Representation of a task in GitHub"""

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
        """ Translates GitHub status into SDE status """
        if self.status in self.done_statuses:
            return 'DONE'
        else:
            return 'TODO'

    def get_timestamp(self):
        """ Returns a datetime object """
        return datetime.strptime(self.timestamp,
                                 '%Y-%m-%dT%H:%M:%SZ')
                                 
class GitHubConnector(AlmConnector):
    alm_name = 'GitHub'
    alm_card_type = 'github_issue_type'
    alm_new_status = 'github_new_status'
    alm_done_statuses = 'github_done_statuses'
    github_duplicate_label = 'github_duplicate_label'
    alm_project_version = 'alm_project_version'

    def __init__(self, config, alm_plugin):
        """ Initializes connection to GitHub """
        super(GitHubConnector, self).__init__(config, alm_plugin)

        config.add_custom_option(self.alm_card_type, 'Issue type represented by labels on GitHub',
                default='')
        config.add_custom_option(self.alm_new_status, 'Status to set for new tasks in GitHub',
            default='open')
        config.add_custom_option(self.alm_done_statuses, 'Statuses that signify a task is Done in GitHub',
            default='closed')
        config.add_custom_option(self.github_duplicate_label, 'GitHub label for duplicate issues',
            default='duplicate')
        config.add_custom_option(self.alm_project_version, 'GitHub milestone',
            default='')
        self.alm_task_title_prefix = 'SDE '
        
    def initialize(self):
        super(GitHubConnector, self).initialize()

        #Verify that the configuration options are set properly
        for item in [self.alm_new_status, self.alm_done_statuses, self.github_duplicate_label]:
            if not self.config[item]:
                raise AlmException('Missing %s in configuration' % item)

        self.config[self.alm_done_statuses] = (
                self.config[self.alm_done_statuses].split(','))

    def alm_connect_server(self):
        """ Verifies that GitHub connection works """
        #Check if user can successfully authenticate and retrieve user profile
        try:
            user_info = self.alm_plugin.call_api('user')
        except APIError, err:
            raise AlmException('Unable to connect to GitHub service (Check server URL, '
                    'user, pass). Reason: %s' % str(err))
                    
        if user_info.get('message'):
            raise AlmException('Could not authenticate GitHub user %s: %s' % (self.config['alm_user'], user_info['message']))
            
    def alm_connect_project(self):
        """ Verifies that the GitHub repo exists """
        self.project_uri = self.config['alm_project']

        # Check if GitHub repo is accessible
        try:
            repo_info = self.alm_plugin.call_api('repos/%s' % self.project_uri)
        except APIError, err:
            raise AlmException('Unable to find GitHub repo. Reason: %s' % err)
           
        if repo_info.get('message'):
            raise AlmException('Error accessing GitHub repository %s: %s' % self.project_uri, repo_info['message'])
    
    def github_get_milestone_id(self, milestone_name):
        if not milestone_name:
            return None

        try:
            milestone_list = self.alm_plugin.call_api('repos/%s/milestones' % self.project_uri)
        except APIError, err:
            logger.error(err)
            raise AlmException('Unable to get milestone %s from GitHub' % milestone_name)
    
        for milestone in milestone_list:
            if milestone['title'] == milestone_name:
                return milestone['number']

        raise AlmException('Unable to find milestone %s from GitHub' % milestone_name)
            
    def alm_get_task(self, task):
        task_id = task['title']
        milestone_name = self.config[self.alm_project_version]
        
        try:
            # We need to perform 2 API calls to search open and closed issues
            open_issues = self.alm_plugin.call_api('legacy/issues/search/%s/%s/%s' % 
                            (self.project_uri, self.config[self.alm_new_status], urlencode_str(task_id)))
            closed_issues = self.alm_plugin.call_api('legacy/issues/search/%s/%s/%s' % 
                            (self.project_uri, self.config[self.alm_done_statuses][0], urlencode_str(task_id)))
            issues_list = open_issues['issues']
            issues_list.extend(closed_issues['issues'])
        except APIError, err:
            logger.error(err)
            raise AlmException('Unable to get task %s from GitHub' % task_id)
        
        if (not issues_list):
            return None
        
        if len(issues_list) > 1:
            index = 0
            
            while index < len(issues_list):
                issue = issues_list[index]
                duplicate_label = self.config[self.github_duplicate_label]
                
                if issue['labels'].count(duplicate_label) > 0:
                    issues_list.pop(index)
                else:
                    index = index + 1
                            
            if len(issues_list) > 1:
                raise AlmException('Found multiple issues with the title %s in milestone %s that are not labeled as duplicates' % (task_id, milestone_name))
            elif not issues_list:
                return None
                
        logger.info('Found task: %s', task_id)
        return GitHubTask(task_id,
                              issues_list[0]['number'],
                              issues_list[0]['state'],
                              issues_list[0]['updated_at'],
                              self.config[self.alm_done_statuses])        

    def alm_add_task(self, task):
        milestone_name = self.config[self.alm_project_version]

        try:
            create_args = { 
                'title': task['title'],
                'body': self.sde_get_task_content(task),
                'labels': [self.config[self.alm_card_type]],
            }
            
            milestone_id = self.github_get_milestone_id(milestone_name)
            if milestone_id:
                create_args['milestone'] = milestone_id

            new_issue = self.alm_plugin.call_api('repos/%s/issues' % self.project_uri,
                    method = self.alm_plugin.URLRequest.POST, args = create_args)
            logger.debug('Task %s added to GitHub Project', task['id'])
        except APIError, err:
            raise AlmException('Unable to add task %s to GitHub because of %s' % 
                    (task['id'], err))
        
        if new_issue.get('errors'):
            raise AlmException('Unable to add task GitHub to %s. Reason: %s - %s' % 
                    (task['id'], str(new_issue['errors']['code']), 
                    str(new_issue['errors']['field'])))

        # API returns JSON of the new issue
        alm_task = GitHubTask(task['title'],
                              new_issue['number'],
                              new_issue['state'],
                              new_issue['updated_at'],
                              self.config[self.alm_done_statuses])        

        if (self.config['alm_standard_workflow'] and (task['status'] == 'DONE' or
                task['status'] == 'NA')):
            self.alm_update_task_status(alm_task, task['status'])
            
        return 'Repository: %s, Issue: %s' % (self.config['alm_project'],
                                           alm_task.get_alm_id())
                                           
    def alm_update_task_status(self, task, status):
        if not task or not self.config['alm_standard_workflow']:
            logger.debug('Status synchronization disabled')
            return
            
        if status == 'DONE' or status=='NA':
            try:
                update_args = {
                    'state':self.config[self.alm_done_statuses][0]
                }
                result = self.alm_plugin.call_api('repos/%s/issues/%s' % (self.project_uri, task.get_alm_id()),
                        args=update_args, method=URLRequest.POST)
            except APIError, err:
                raise AlmException('Unable to update task status to DONE '
                                   'for issue: %s in GitHub because of %s' %
                                   (task.get_alm_id(), err))
        elif status== 'TODO':
            try:
                update_args = {
                    'state':self.config[self.alm_new_status]
                }
                result = self.alm_plugin.call_api('repos/%s/issues/%s' % (self.project_uri, task.get_alm_id()),
                        args=update_args, method=URLRequest.PUT)
            except APIError, err:
                raise AlmException('Unable to update task status to TODO for '
                                   'issue: %s in GitHub because of %s' %
                                   (task.get_alm_id(), err))
        
        if (result and result.get('errors')):
            raise AlmException('Unable to update status of task %s to %s. Reason: %s - %s' % 
                    (task['id'], status, str(new_issue['errors']['code']), 
                    str(new_issue['errors']['field']))) 
                    
        logger.debug('Status changed to %s for task %s in GitHub' %
                (status, task.get_alm_id()))
                
    def alm_disconnect(self):
        pass