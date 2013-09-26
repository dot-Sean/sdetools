import re
import os
import sys

from urllib2 import HTTPError
from mock import MagicMock

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))))
from sdetools.alm_integration.tests.alm_response_generator import AlmResponseGenerator

class GitHubResponseGenerator(AlmResponseGenerator):
    GITHUB_STATUS_NAMES = ['open', 'closed']
    REST_API_TARGETS = {
        'get_user': 'user',
        'get_repo': 'repos/%s',
        'get_milestones': 'repos/%s/milestones',
        'get_task': 'legacy/issues/search/%s',
        'post_issue': 'repos/%s/issues',
        'update_status': 'repos/%s/issues/[0-9]*$'
    }

    def __init__(self, host, repo_org, repo_name, project_milestone, username, protocol='http'):
        initial_task_status = self.GITHUB_STATUS_NAMES[0]
        test_dir = os.path.dirname(os.path.abspath(__file__)) 
        super(GitHubResponseGenerator, self).__init__(initial_task_status, test_dir)

        self.project_uri = '%s/%s' % (self.urlencode_str(repo_org), self.urlencode_str(repo_name))
        self.api_url = '%s://%s/%s' % (protocol, host, self.project_uri)
        self.project_milestone = project_milestone
        self.username = username

    def get_response(self, target, flag, data, method):
        if target == self.REST_API_TARGETS['get_user']:
            return self.get_user(flag)
        elif target == self.REST_API_TARGETS['get_repo'] % self.project_uri:
            return self.get_repo(flag)
        elif target == self.REST_API_TARGETS['get_milestones'] % self.project_uri:
            return self.get_milestones(flag)
        elif self.REST_API_TARGETS['get_task'] % self.project_uri in target:
            return self.get_task(flag, target)
        elif target == self.REST_API_TARGETS['post_issue'] % self.project_uri:
            return self.post_issue(flag, data)
        elif re.match(self.REST_API_TARGETS['update_status'] % self.project_uri, target):
            return self.update_status(flag, target, data)
        else:
            self.raise_error('404')

    def raise_error(self, error_code):
        fp_mock = MagicMock()
        if error_code == '401':
            fp_mock.read.return_value = '{"message":"Requires authentication","documentation_url":"http://developer.github.com/v3"}'
            raise HTTPError('%s' % self.api_url, '401', 'Unauthorized user', '', fp_mock)
        elif error_code == '404':
            fp_mock.read.return_value = '{"message":"Not found","documentation_url":"http://developer.github.com/v3"}'
            raise HTTPError('%s' % self.api_url, '404', 'Not found', '', fp_mock)


    """
       Response functions 
    """
    def get_user(self, flag):
        if not flag:
            return self.get_json_from_file('user')
        else:
            self.raise_error('401')

    def get_repo(self, flag):
        if not flag:
            return self.get_json_from_file('repo')
        else:
            self.raise_error('404')

    def get_milestones(self, flag):
        if not flag:
            return self.get_json_from_file('milestones')
        else:
            return []

    def get_task(self, flag, target):
        params = target.split('/')
        state = params[-2]
        task_name = params[-1]
        task_name = task_name.split(self.urlencode_str(':'))[0]

        if not flag and self.get_alm_task(task_name):
            status = self.get_alm_task('%s:status' % task_name)
            if status == state:
                response = self.get_json_from_file('issues')
                issue = response['issues'][0]
                issue['number'] = self.get_alm_task(task_name)
                issue['state'] = state
                issue['title'] = task_name

                return response

        return {"issues": []}

    def post_issue(self, flag, data):
        if not flag:
            name = data['title'].split(':')[0]
            id = name.split('T')[1]
            self.add_alm_task(name, id)
            response = self.generate_issue(name, id, 'open')

            return response
        else:
            self.raise_error('404')

    def update_status(self, flag, target, data):
        task_id = target.split('/')[4]

        if not flag:
            if self.get_alm_task(task_id) and data['state']:
                name = self.get_alm_task(task_id)
                status = data['state']
                response = self.generate_issue(name, task_id, status)
                self.update_alm_task('%s:status' % name, status)

                return response
            else:
                self.raise_error('404')
        else:
            self.raise_error('401')

    """
       JSON Generator 
    """
    def generate_issue(self, name, id, status):
        response = self.get_json_from_file('issue')
        response['number'] = id
        response['state'] = status
        response['title'] = name

        return response
