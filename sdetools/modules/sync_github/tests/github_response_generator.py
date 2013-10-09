import os

from urllib2 import HTTPError
from mock import MagicMock

from sdetools.alm_integration.tests.alm_response_generator import AlmResponseGenerator
from sdetools.sdelib.commons import urlencode_str


class GitHubResponseGenerator(AlmResponseGenerator):
    STATUS_NAMES = ['open', 'closed']

    def __init__(self, host, repo_org, repo_name, project_milestone, username, protocol='http'):
        initial_task_status = self.STATUS_NAMES[0]
        test_dir = os.path.dirname(os.path.abspath(__file__)) 
        super(GitHubResponseGenerator, self).__init__(initial_task_status, test_dir)

        self.project_uri = '%s/%s' % (urlencode_str(repo_org), urlencode_str(repo_name))
        self.api_url = '%s://%s/%s' % (protocol, host, self.project_uri)
        self.project_milestone = project_milestone
        self.username = username
        self.rest_api_targets = {
            'user': 'get_user',
            'repos/%s$' % self.project_uri: 'get_repo',
            'repos/%s/milestones' % self.project_uri: 'get_milestones',
            'legacy/issues/search/%s' % self.project_uri: 'get_task',
            'repos/%s/issues$' % self.project_uri: 'post_issue',
            'repos/%s/issues/[0-9]*$' % self.project_uri: 'update_status'
        }

    def raise_error(self, error_code, return_value=None):
        fp_mock = MagicMock()
        if error_code == '401':
            fp_mock.read.return_value = '{"message":"Requires authentication","documentation_url":"http://developer.github.com/v3"}'
            raise HTTPError('%s' % self.api_url, '401', 'Unauthorized user', '', fp_mock)
        elif error_code == '404':
            fp_mock.read.return_value = '{"message":"Not found","documentation_url":"http://developer.github.com/v3"}'
            raise HTTPError('%s' % self.api_url, '404', 'Not found', '', fp_mock)
        else:
            fp_mock.read.return_value = 'Error'
            raise HTTPError('%s' % self.api_url, error_code, 'Error', '', fp_mock)

    """
       Response functions 
    """
    def get_user(self, target, flag, data, method):
        if not flag:
            return self.get_json_from_file('user')
        else:
            self.raise_error('401')

    def get_repo(self, target, flag, data, method):
        if not flag:
            return self.get_json_from_file('repo')
        elif flag == 'private-false':
            repo = self.get_json_from_file('repo')
            repo['private'] = False

            return repo
        else:
            self.raise_error('404')

    def get_milestones(self, target, flag, data, method):
        if not flag:
            return self.get_json_from_file('milestones')
        else:
            return []

    def get_task(self, target, flag, data, method):
        params = target.split('/')
        state = params[-2]
        task_name = params[-1]
        task_name = task_name.split(urlencode_str(':'))[0]
        task_number = self.extract_task_number_from_title(task_name)
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

    def post_issue(self, target, flag, data, method):
        if not flag:
            task_number = self.extract_task_number_from_title(data['title'])
            self.add_alm_task(task_number)
            response = self.generate_issue(task_number, 'open')

            return response
        else:
            self.raise_error('404')

    def update_status(self, target, flag, data, method):
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
