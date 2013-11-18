from sdetools.sdelib.testlib.response_generator import ResponseGenerator
from sdetools.sdelib.commons import urlencode_str


class GitHubResponseGenerator(ResponseGenerator):
    def __init__(self, config, test_dir=None):
        self.project_uri = '%s/%s' % (urlencode_str(config['github_repo_owner']), urlencode_str(config['alm_project']))
        self.project_milestone = config['alm_project_version']
        self.username = config['alm_user']
        statuses = ['open', 'closed']
        rest_api_targets = {
            '/user': 'get_user',
            '/repos/%s$' % self.project_uri: 'get_repo',
            '/repos/%s/milestones' % self.project_uri: 'get_milestones',
            '/legacy/issues/search/%s' % self.project_uri: 'get_task',
            '/repos/%s/issues$' % self.project_uri: 'post_issue',
            '/repos/%s/issues/[0-9]*$' % self.project_uri: 'update_status'
        }
        super(GitHubResponseGenerator, self).__init__(rest_api_targets, statuses, test_dir)

    def raise_error(self, error_code, message=None):
        if message is None:
            if error_code == '401':
                message = {
                    "message":"Requires authentication",
                    "documentation_url":"http://developer.github.com/v3"
                }
            elif error_code == '404':
                message = {
                    "message":"Not found",
                    "documentation_url":"http://developer.github.com/v3"
                }
            elif error_code == '422':
                message = {
                    "message":"Validation Failed",
                    "errors": [{
                        "resource": "Issue",
                        "field": "title",
                        "code": "missing_field"
                    }]
                }
            else:
                message = {
                    "message":"Error",
                }
        super(GitHubResponseGenerator, self).raise_error(error_code, message)

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
        elif flag == '401':
            self.raise_error('401')
        else:
            return []

    def get_task(self, target, flag, data, method):
        params = target.split('/')
        state = params[-2]
        task_name = params[-1]
        task_name = task_name.split(urlencode_str(':'))[0]
        task_number = self.extract_task_number_from_title(task_name)
        task = self.generator_get_task(task_number)

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
            self.generator_add_task(task_number)
            response = self.generate_issue(task_number, 'open')

            return response
        elif flag == '422':
            self.raise_error('422')
        else:
            self.raise_error('404')

    def update_status(self, target, flag, data, method):
        task_id = target.split('/')[5]

        if not flag:
            if self.generator_get_task(task_id) and data['state']:
                status = data['state']
                response = self.generate_issue(task_id, status)
                self.generator_update_task(task_id, 'status', status)

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
