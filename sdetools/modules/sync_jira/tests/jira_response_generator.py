import re

from urllib2 import HTTPError
from sdetools.sdelib.testlib.response_generator import ResponseGenerator, RESPONSE_HEADERS
from sdetools.extlib.SOAPpy.Types import structType, faultType


class JiraResponseGenerator(ResponseGenerator):
    PROJECT_ID = '10000'
    JIRA_ISSUE_TYPES = ["Bug", "New Feature", "Task", "Improvement", "Sub-task"]
    JIRA_PRIORITY_NAMES = ['Blocker', 'Critical', 'Major', 'Minor', 'Trivial']
    JIRA_STATUS_NAMES = ['Open', 'In Progress', 'Resolved', 'Closed', 'Open']
    JIRA_TRANSITION_NAMES = ['Start Progress', 'Resolve Issue', 'Close Issue', 'Reopen Issue']

    def __init__(self, config, test_dir=None):
        self.base_url = '%s://%s' % (config['alm_method'], config['alm_server'])
        self.api_url = '%s/%s' % (self.base_url, 'rest/api/2')
        self.project_key = config['alm_project']
        self.project_version = config['alm_project_version']
        resource_templates = ['issue.json', 'project.json', 'project_version.json']
        rest_api_targets = {
            '/rest/api/2/project$': 'get_projects',
            '/rest/api/2/project/%s/versions' % self.project_key: 'get_project_versions',
            '/rest/api/2/issue/createmeta': 'get_create_meta',
            '/rest/api/2/issuetype': 'get_issue_types',
            '/rest/api/2/search\?jql=project%%3D\'%s\'%%20AND%%20summary~.*' % self.project_key: 'get_issue',
            '/rest/api/2/issue/%s-\S.*/remotelink$' % self.project_key: 'post_remote_link',
            '/rest/api/2/issue$': 'post_issue',
            '/rest/api/2/issue/%s-[0-9]*$' % self.project_key: 'update_issue',
            '/rest/api/2/issue/%s-\S.*/transitions$' % self.project_key: 'update_status',
            'https://jira-server:5000/rpc/soap/jirasoapservice-v2': 'jira_soap_service'
        }
        super(JiraResponseGenerator, self).__init__(rest_api_targets, resource_templates, test_dir)

    def init_with_resources(self):
        project_data = {
            'self': '%s/project/%s' % (self.api_url, self.project_key),
            'id': self.PROJECT_ID,
            'key': self.project_key,
        }
        self.generator_add_resource('project', self.PROJECT_ID, project_data)

    def jira_soap_service(self, target, flag, data, method):
        return RESPONSE_HEADERS, ''

    def get_proxy_response(self, args):
        """
            Triage SOAP calls
            args: [method_name, response_flag, auth_token{, *data}]
        """
        method_name = args[0]
        flags = args[1]
        token = args[2]

        try:
            if not token:
                self.raise_error('401')
            if method_name == 'getProjectByKey':
                flag = flags.get('get_projects')
                headers, response = self.get_projects('', flag, None, None)
                return response[0]
            elif method_name == 'getIssueTypes':
                flag = flags.get('get_issue_types')
                headers, response = self.get_issue_types('', flag, None, None)
                return response
            elif method_name == 'login':
                flag = flags.get('get_auth_token')
                headers, response = self.get_auth_token(flag)
                return response
            elif method_name == 'getStatuses':
                flag = flags.get('get_statuses')
                headers, response = self.get_statuses(flag)
                return response
            elif method_name == 'getPriorities':
                flag = flags.get('get_priorities')
                headers, response = self.get_priorities(flag)
                return response
            elif method_name == 'getVersions':
                flag = flags.get('get_project_versions')
                headers, response = self.get_project_versions('', flag, None, None)
                return response
            elif method_name == 'getFieldsForCreate':
                flag = flags.get('get_fields_for_create')
                headers, response = self.get_fields_for_create(flag)
                return response
            elif method_name == 'getIssuesFromJqlSearch':
                flag = flags.get('get_issue')
                task_name = re.sub(r".*summary~", '', args[3])
                headers, rest_response = self.get_issue('', flag, None, 'GET', task_name)
                issues = rest_response.get('issues')

                if not issues:
                    return []
                else:
                    issue = issues[0].get('fields')
                    issue['status'] = issue['status']['id']
                    issue['key'] = issues[0].get('key')

                    return [structType(data=issue)]
            elif method_name == 'createIssue':
                flag = flags.get('post_issue')
                headers, response = self.post_issue('', flag, args[3], 'GET')
                return response
            elif method_name == 'updateIssue':
                flag = flags.get('update_issue') or flags.get('update_version')
                if not flag:
                    pass
                else:
                    self.raise_error('401')
            elif method_name == 'deleteIssue':
                flag = flags.get('delete_issue') or flags.get('delete_issue')
                if not flag:
                    task_number = args[3].split('-')[1]
                    self.generator_remove_resource('issue', task_number)
                    return ''
                else:
                    self.raise_error('401')
            elif method_name == 'getAvailableActions':
                flag = flags.get('update_status')
                headers, response = self.update_status(args[3], flag, '{}', 'GET')
                return response.get('transitions')
            elif method_name == 'progressWorkflowAction':
                flag = flags.get('update_status')
                transition_data = {"transition": {"id": args[4]}}
                headers, response = self.update_status(args[3], flag, transition_data, 'POST')
                return response
            elif method_name == 'getFieldsForEdit':
                flag = flags.get('get_fields_for_edit')
                headers, response = self.get_fields_for_edit(flag)
                return response
            else:
                self.raise_error('404')
        except HTTPError as err:
            # Return a faultType object instead
            raise faultType(err.code, err.msg)

    """
       Response functions 
    """
    def update_issue(self, target, flag, data, method):
        if not flag:
            task_id = target.split('/')[5]
            task_number = task_id.split('-')[1]

            if task_number:
                if method == 'POST':
                    version_name = data['update']['versions'][0]['add']['name']
                    self.generator_update_resource('issue', task_number, {'version': version_name})

                    return RESPONSE_HEADERS, {
                        "id": "10000",
                        "key": "TEST-24",
                        "self": "http://www.example.com/jira/rest/api/2/issue/10000"
                    }
                elif method == 'DELETE':
                    self.generator_remove_resource('issue', task_number)
                    return RESPONSE_HEADERS, ''

            self.raise_error('500')
        else:
            self.raise_error('400')

    def get_fields_for_create(self, flag):
        if not flag:
            return RESPONSE_HEADERS, self.get_json_from_file('createFields')
        else:
            self.raise_error('401')

    def get_fields_for_edit(self, flag):
        if not flag:
            return RESPONSE_HEADERS, self.get_json_from_file('editFields')
        else:
            self.raise_error('401')

    def get_auth_token(self, flag):
        if not flag:
            return RESPONSE_HEADERS, 'authToken12345'
        else:
            self.raise_error('401')

    def get_projects(self, target, flag, data, method):
        if not flag:
            return RESPONSE_HEADERS, self.generator_get_all_resource('project')
        else:
            self.raise_error('500')

    def get_issue_types(self, target=None, flag=None, data=None, method=None):
        response = []

        if not flag:
            for i in range(1, len(self.JIRA_ISSUE_TYPES) + 1):
                response.append(self.generate_issue_type(i))
        return RESPONSE_HEADERS, response

    def get_project_versions(self, target, flag, data, method):
        if not flag:
            response = []
            response.append(self.generate_project_version('1.2'))

            if self.project_version is not None:
                response.append(self.generate_project_version())

            return RESPONSE_HEADERS, response
        else:
            self.raise_error('404')

    def get_create_meta(self, target, flag, data, method):
        if not flag:
            response = {'expands': 'projects'}
            _project = self.generate_project()

            headers, _project['issuetypes'] = self.get_issue_types(flag=flag)
            response['projects'] = [_project]

            return RESPONSE_HEADERS, response
        else:
            self.raise_error('403')

    def get_issue(self, target, flag, data, method, name=None):
        if not flag:
            response = {
                'expand': 'names,schema',
                'startAt': 0,
                'maxResults': 50,
                'total': 0,
                'issues': []
            }

            if not name:
                params = self.get_url_parameters(target)
                name = re.search('(?<=summary~).*', params['jql'][0].replace('\\', '')).group(0)

            task_number = self.extract_task_number_from_title(name)
            task = self.generator_get_resource('issue', task_number)

            if task:
                response['issues'].append(task)
                response['total'] = 1

            return RESPONSE_HEADERS, response
        else:
            self.raise_error('400')

    def update_status(self, target, flag, data, method):
        if not flag and method == 'GET':
            response = {"expand": "transitions"}
            transitions = []

            for i in range(1, len(self.JIRA_TRANSITION_NAMES) + 1):
                transitions.append(self.generate_transition(i))
            response['transitions'] = transitions

            return RESPONSE_HEADERS, response
        elif not flag and data and method == 'POST':
            transition_id = data['transition']['id']
            task_number = re.search('(?<=%s-)[0-9a-zA-z]+' % self.project_key, target).group(0)

            if not self.generator_get_resource('issue', task_number):
                self.raise_error('404')

            updated_status = {'fields': {'status': self.generate_status(int(transition_id) + 1)}}
            self.generator_update_resource('issue', task_number, updated_status)

            return RESPONSE_HEADERS, None
        else:
            self.raise_error(flag)

    def post_issue(self, target, flag, data, method):
        if not flag and data:
            task_name = None
            if data.get('fields') and data.get('fields').get('summary'):
                task_name = data.get('fields').get('summary')
            elif data.get('summary'):
                task_name = data.get('summary')

            if task_name is not None:
                task_id = self.extract_task_number_from_title(task_name)
                data['id'] = task_id
                data['key'] = '%s-%s' % (self.project_key, task_id)
                data['self'] = '%s/issue/%s' % (self.api_url, task_id)

                if data.get('fields') is None:
                    data['fields'] = {}
                if data['fields'].get('status') is None:
                    data['fields']['status'] = self.generate_status(1)

                self.generator_add_resource('issue', task_id, data)

                return RESPONSE_HEADERS, self.generate_resource_from_template('issue', data)
        self.raise_error('400', '{"errorMessages":["Missing field"],"errors":{}}')

    def post_remote_link(self, target, flag, data, method):
        if not flag:
            task_id = target.split('/')[5]

            if data and data.get('object') and data.get('object').get('title'):
                task_number = task_id.split('-')[1]
                response = {
                    'id': task_number,
                    'self': ('%s/rest/api/issue/%s/remotelink/%s' % (self.base_url, task_id, task_number))
                }

                return RESPONSE_HEADERS, response
            else:
                self.raise_error('400', '{"errorMessage": [], "errors": {"title": "missing field"}}')
        else:
            self.raise_error(flag)

    def get_statuses(self, flag):
        response = []
        if not flag:
            # We can skip the last entry since it is a repeat
            for i in range(1, len(self.JIRA_STATUS_NAMES)):
                response.append(self.generate_status(i))

        return RESPONSE_HEADERS, response

    def get_priorities(self, flag):
        response = []
        if not flag:
            for i in range(1, len(self.JIRA_PRIORITY_NAMES) + 1):
                response.append(self.generate_priority(i))

        return RESPONSE_HEADERS, response

    """
       JSON Generator 
    """
    def generate_transition(self, transition_id):
        transition = self.get_json_from_file('transition')
        transition['id'] = '%d' % transition_id
        transition['name'] = self.JIRA_TRANSITION_NAMES[transition_id - 1]
        transition['to']['self'] = "%s/status/%d" % (self.api_url, transition_id)
        transition['to']['iconUrl'] = '%s/images/icons/status%d.gif' % (self.base_url, transition_id)
        transition['to']['name'] = self.JIRA_STATUS_NAMES[transition_id]
        transition['to']['id'] = transition_id

        return transition

    def generate_status(self, id):
        status_name = self.JIRA_STATUS_NAMES[id - 1]
        status = {
            'self': '%s/status/%s' % (self.api_url, id),
            'description': 'Issue description',
            'iconUrl': '%s/images/icons/status_%s.gif' % (self.base_url, status_name),
            'name': status_name,
            'id': '%s' % id
        }

        return status

    def generate_priority(self, id):
        priority_name = self.JIRA_PRIORITY_NAMES[id - 1]
        priority = self.get_json_from_file('priority')
        priority['self'] = '%s/priority/%s' % (self.api_url, id)
        priority['iconUrl'] = ('%s/images/icons/priority_%s.gif' % (self.base_url, priority_name))
        priority['name'] = priority_name
        priority['id'] = id

        return priority

    def generate_project(self):
        response = self.get_json_from_file('project')
        response['self'] = '%s/project/%s' % (self.api_url, self.project_key)
        response['id'] = self.PROJECT_ID
        response['key'] = self.project_key

        return response

    def generate_issue_type(self, issue_id):
        issue_type_name = self.JIRA_ISSUE_TYPES[int(issue_id) - 1]
        issue_type = self.get_json_from_file('issue_type')
        issue_type['self'] = '%s/issueType/%s' % (self.api_url, issue_id)
        issue_type['id'] = issue_id
        issue_type['description'] = 'Issue type %s, %s' % (issue_id, issue_type_name)
        issue_type['name'] = issue_type_name

        if issue_type_name == 'Sub-task':
            issue_type['subTask'] = True

        return issue_type

    def generate_project_version(self, project_version=None):
        version = self.get_json_from_file('project_version')
        version['self'] = "%s/version/%s" % (self.api_url, self.project_version)
        version['id'] = self.project_version
        if project_version:
            version['id'] = project_version

        return version


class JiraCustomFieldResponseGenerator(JiraResponseGenerator):

    def __init__(self, config, test_dir=None):
        super(JiraCustomFieldResponseGenerator, self).__init__(config, test_dir)

    def get_create_meta(self, target, flag, data, method):
        if not flag:
            response = {'expands': 'projects'}
            _project = self.generate_project()

            headers, _project['issuetypes'] = self.get_issue_types(flag=flag)

            _project['issuetypes'][0]['fields']['customField_10001'] = {
                "required": True,
                "name": "custom_text_field",
                "schema": {
                    "customId": 10001,
                    "type": "string",
                    "custom": "com.atlassian.jira.plugin.system.customfieldtypes:textfield"
                }
            }
            _project['issuetypes'][0]['fields']['customField_10002'] = {
                "operations": ["add", "set", "remove"],
                "required": True,
                "allowedValues": [{
                    "self": "http://server/rest/api/2/customFieldOption/10119",
                    "id": "10119",
                    "value": "option1"
                }, {
                    "self": "http://server/rest/api/2/customFieldOption/10120",
                    "id": "10120",
                    "value": "option2"
                }],
                "name": "custom_multi_checkboxes",
                "schema": {
                    "items": "string",
                    "customId": 10002,
                    "type": "array",
                    "custom": "com.atlassian.jira.plugin.system.customfieldtypes:multicheckboxes"
                }
            }
            _project['issuetypes'][0]['fields']['customField_10003'] = {
                "operations": ["set"],
                "required": True,
                "allowedValues": [{
                    "self": "http://server/rest/api/2/customFieldOption/10139",
                    "id": "10139",
                    "value": "radio1"
                }, {
                    "self": "http://server/rest/api/2/customFieldOption/10130",
                    "id": "10130",
                    "value": "radio2"
                }],
                "name": "custom_radio_buttons",
                "schema": {
                    "customId": 10003,
                    "type": "string",
                    "custom": "com.atlassian.jira.plugin.system.customfieldtypes:radiobuttons"
                }
            }
            response['projects'] = [_project]

            return RESPONSE_HEADERS, response
        else:
            self.raise_error('403')


class JiraInvalidProjectIssueTypeResponseGenerator(JiraResponseGenerator):

    def __init__(self, config, test_dir=None):
        super(JiraInvalidProjectIssueTypeResponseGenerator, self).__init__(config, test_dir)

    def get_create_meta(self, target, flag, data, method):
        if not flag:
            response = {'expands': 'projects'}
            _project = self.generate_project()

            _project['issuetypes'] = [self.generate_issue_type(0)]
            response['projects'] = [_project]

            return RESPONSE_HEADERS, response
        else:
            self.raise_error('403')