from sdetools.sdelib.testlib.response_generator import ResponseGenerator
from sdetools.sdelib.commons import urlencode_str


class GitHubResponseGenerator(ResponseGenerator):
    def __init__(self, config, test_dir=None):
        project_uri = '%s/%s' % (urlencode_str(config['github_repo_owner']), urlencode_str(config['alm_project']))
        self.project_milestone = config['alm_project_version']
        self.username = config['alm_user']
        self.alm_project = config['alm_project']
        resource_templates = ['user.json', 'issue.json', 'repo.json', 'milestone.json']
        rest_api_targets = {
            'user': 'get_user',
            'repos/%s$' % project_uri: 'get_repo',
            'repos/%s/milestones' % project_uri: 'get_milestones',
            'legacy/issues/search/%s' % project_uri: 'get_issue',
            'repos/%s/issues$' % project_uri: 'post_issue',
            'repos/%s/issues/[0-9]*$' % project_uri: 'update_status'
        }
        super(GitHubResponseGenerator, self).__init__(rest_api_targets, resource_templates, test_dir)

    def init_with_resources(self):
        self.generator_add_resource('user', resource_data={'login': self.username})
        self.generator_add_resource('repo', resource_data={'name': self.alm_project})
        self.generator_add_resource('milestone', resource_data={'title': self.project_milestone})

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
            return self.generator_get_all_resource('user')[0]
        else:
            self.raise_error('401')

    def get_repo(self, target, flag, data, method):
        if not flag:
            return self.generator_get_all_resource('repo')[0]
        elif flag == 'private-false':
            repo = self.generator_get_all_resource('repo')[0]
            repo['private'] = False

            return repo
        else:
            self.raise_error('404')

    def get_milestones(self, target, flag, data, method):
        if not flag:
            return self.generator_get_all_resource('milestone')
        elif flag == '401':
            self.raise_error('401')
        else:
            return []

    def get_issue(self, target, flag, data, method):
        params = target.split('/')
        state = params[-2]
        task_number = self.extract_task_number_from_title(params[-1])

        return {"issues": self.generator_get_filtered_resource('issue', {'number': task_number, 'state': state})}

    def post_issue(self, target, flag, data, method):
        if not flag:
            task_number = self.extract_task_number_from_title(data['title'])
            data['state'] = 'open'
            data['number'] = task_number
            data['id'] = task_number
            self.generator_add_resource('issue', task_number, data)

            return self.generate_resource_from_template('issue', data)
        elif flag == '422':
            self.raise_error('422')
        else:
            self.raise_error('404')

    def update_status(self, target, flag, data, method):
        task_number = target.split('/')[-1]

        if not flag:
            if self.generator_resource_exists('issue', task_number) and self.is_data_valid(data, ['state']):
                self.generator_update_resource('issue', task_number, {'state': data['state']})

                return self.generator_get_resource('issue', task_number)
            else:
                self.raise_error('404')
        else:
            self.raise_error('401')

    """
       JSON Generator 
    """
    def generator_generate_task_template(self):
        return self.get_json_from_file('issue')
