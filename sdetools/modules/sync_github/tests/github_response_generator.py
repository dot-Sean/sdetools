import re
import os
import sys

from urllib2 import HTTPError
from mock import MagicMock

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))))
from sdetools.alm_integration.tests.alm_response_generator import AlmResponseGenerator
from sdetools.sdelib.commons import urlencode_str

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

        self.project_uri = '%s/%s' % (urlencode_str(repo_org), urlencode_str(repo_name))
        self.api_url = '%s://%s/%s' % (protocol, host, self.project_uri)
        self.project_milestone = project_milestone
        self.username = username

    def get_response(self, target, flag, data, method):
        if target == self.REST_API_TARGETS['get_user']:
            return self.get_user(flag.get('get_user'))
        elif target == self.REST_API_TARGETS['get_repo'] % self.project_uri:
            return self.get_repo(flag.get('get_repo'))
        elif target == self.REST_API_TARGETS['get_milestones'] % self.project_uri:
            return self.get_milestones(flag.get('get_milestones'))
        elif self.REST_API_TARGETS['get_task'] % self.project_uri in target:
            return self.get_task(flag.get('get_task'), target)
        elif target == self.REST_API_TARGETS['post_issue'] % self.project_uri:
            return self.post_issue(flag.get('post_issue'), data)
        elif re.match(self.REST_API_TARGETS['update_status'] % self.project_uri, target):
            return self.update_status(flag.get('update_status'), target, data)
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
        elif flag == 'private-false':
            repo = self.get_json_from_file('repo')
            repo['private'] = False

            return repo
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
        task_name = task_name.split(urlencode_str(':'))[0]
        task_number = self.get_task_number_from_title(task_name)
        task = self.get_alm_task(task_number)
        if not flag and task:
            status = task.get('status')
            if status == state:
                response = self.get_json_from_file('issues')
                issue = response['issues'][0]
                issue['number'] = task_number
                issue['state'] = state
                issue['title'] = task_name

                return response

        return {"issues": []}

    def post_issue(self, flag, data):
        if not flag:
            task_number = self.get_task_number_from_title(data['title'])
            self.add_alm_task(task_number)
            response = self.generate_issue(task_number, 'open')

            return response
        else:
            self.raise_error('404')

    def update_status(self, flag, target, data):
        task_id = target.split('/')[4]

        if not flag:
            if self.get_alm_task(task_id) and data['state']:
                status = data['state']
                response = self.generate_issue(task_id, status)
                self.update_alm_task(task_id, 'status', status)

                return response
            else:
                self.raise_error('404')
        else:
            self.raise_error('401')

    """
       JSON Generator 
    """
    def generate_issue(self, task_id, status):
        response = self.get_json_from_file('issue')
        response['number'] = task_id
        response['state'] = status
        response['title'] = 'T%s' % task_id

        return response
