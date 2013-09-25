import re, os, sys
from urllib2 import HTTPError
from mock import MagicMock

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))))
from sdetools.alm_integration.tests.alm_response_generator import AlmResponseGenerator
from sdetools.extlib.SOAPpy.Types import structType

class JiraResponseGenerator(AlmResponseGenerator):
    api_url = 'rest/api/2'
    PROJECT_ID = '10000'
    JIRA_ISSUE_TYPES = ["Bug", "New Feature", "Task", "Improvement", "Sub-task"]
    JIRA_PRIORITY_NAMES = ['Blocker', 'Critical']
    JIRA_STATUS_NAMES = ['Open', 'In Progress', 'Resolved', 'Closed', 'Open']
    JIRA_TRANSITION_NAMES = ['Start Progress', 'Resolve Issue', 'Close Issue', 'Reopen Issue']
    project_name = 'Test Project'

    def __init__(self, host, project_key, project_version, username, protocol='http'):
        initial_task_status = 1
        test_dir = os.path.dirname(os.path.abspath(__file__)) 
        super(JiraResponseGenerator, self).__init__(initial_task_status, test_dir)
        
        self.base_url = '%s://%s' % (protocol, host)
        self.api_url = '%s/%s' % (self.base_url, self.api_url)
        self.project_key = project_key
        self.project_version = project_version
        self.username = username
    
    def soap_reply(self, args):
        name = args[0]

        if name == 'getIssueTypes':
            return self.get_response('issuetype')
        elif name == 'login':
            return self.get_auth_token()
        elif name == 'getStatuses':
            response = []
            for i in range(1, len(self.JIRA_STATUS_NAMES) + 1):
                response.append(self.generate_status(i))
            return response
        elif name == 'getPriorities':
            response = []
            for i in range(1, len(self.JIRA_PRIORITY_NAMES) + 1):
                response.append(self.generate_priority(i))
            return response
        elif name == 'getProjectByKey':
            return self.get_response('project')[0]
        elif name == 'getVersions':
            return self.get_response('project/%s/versions' % self.project_key)
        elif name == 'getFieldsForCreate':
            return self.get_fields_for_create()
        elif name == 'getIssuesFromJqlSearch':
            task_name = re.sub(r".*summary~", '', args[2])
            rest_response = self.get_issue(None, None, task_name)
            issues = rest_response.get('issues')
            if not issues:
                return []
            else:
                issue = issues[0].get('fields')
                issue['status'] = issue['status']['id']
                issue['key'] = issues[0].get('key')
                return [structType(data=issue)]
        elif name == 'createIssue':
            return self.get_response('issue', data=args[2])
        elif name == 'updateIssue':
            pass
        elif name == 'getAvailableActions':
            return self.update_status(None, None, 'GET', None).get('transitions')
        elif name == 'progressWorkflowAction':
            transition_data = {"transition":{"id":args[3]}}
            return self.update_status(None, args[2], 'POST', transition_data)
        else:
            self.raise_error('404')
    REST_API_TARGETS = {'get_projects':'project',
                        'get_project_versions':'project/%s/versions',
                        'get_create_meta':'issue/createmeta',
                        'get_issue_types':'issuetype',
                        'get_issue':'search?jql=project%%3D\'%s\'%%20AND%%20summary~',
                        'post_remote_link':'issue/%s-\S.*/remotelink$',
                        'post_issue':'issue',
                        'update_status':'issue/%s-\S.*/transitions$'}
    SOAP_TARGETS = ['getIssueTypes']

    def get_response(self, target, flag=None, data=None, method='GET'):

        if target == self.REST_API_TARGETS['get_projects']:
            return self.get_projects(flag)
        elif target == self.REST_API_TARGETS['get_issue_types']:
            return self.get_issue_types(flag)
        elif target == self.REST_API_TARGETS['get_project_versions'] % self.project_key:
            return self.get_project_versions(flag)
        elif target == self.REST_API_TARGETS['get_create_meta']:
            return self.get_create_meta(flag)
        elif self.REST_API_TARGETS['get_issue'] % self.project_key in target:
            return self.get_issue(flag, target)
        elif target == self.REST_API_TARGETS['post_issue']:
            return self.post_issue(flag, data)
        elif re.match(self.REST_API_TARGETS['post_remote_link'] % self.project_key, target):
            id = target.split('/')[1]
            return self.post_remote_link(flag, data, id)
        elif re.match(self.REST_API_TARGETS['update_status'] % self.project_key, target):
            id = target.split('/')[1]
            return self.update_status(flag, id, method, data)
        else:
            self.raise_error('404')

    def raise_error(self, error_code, return_value=None):
        fp_mock = MagicMock()
        
        if error_code == '400':
            message = 'Invalid parameters'
        elif error_code == '403':
            message = 'No permission'
        elif error_code == '404':
            message = 'Not found'
        elif error_code == '500':
            message = 'Server error'

        if not return_value:
            fp_mock.read.return_value = message
        else:
            fp_mock.read.return_value = return_value

        raise HTTPError('%s' % self.api_url, error_code, message, '', fp_mock)

    """
       Response functions 
    """
    def get_fields_for_create(self, flag=None):
        if not flag:
            self.get_json_from_file('createFields')
        else:
            self.raise_error('401')

    def get_auth_token(self, flag=None):
        if not flag:
            return 'authToken12345'
        else:
            self.raise_error('401')

    def get_projects(self, flag):
        if not flag:
            response = []
            response.append(self.generate_project())

            return response
        else:
            self.raise_error('500')

    def get_issue_types(self, flag):
        response = []

        if not flag:
            response.append(self.generate_issue_type('1'))
            response.append(self.generate_issue_type('2'))
            response.append(self.generate_issue_type('3'))
            response.append(self.generate_issue_type('4'))
            response.append(self.generate_issue_type('5'))

        return response

    def get_project_versions(self, flag):
        if not flag:
            response = []

            if self.project_version:
                version = self.get_json_from_file('project_version')
                version['self'] = "%s/version/%s" % (self.api_url, self.project_version)
                version['id'] = self.project_version
                response.append(version)

            return response
        else:
            self.raise_error('404')

    def get_create_meta(self, flag):
        if not flag:
            response = {}
            response['expands'] = 'projects'
            _project = self.generate_project()
            _project['issuetypes'] = self.get_issue_types(flag)
            response['projects'] = [_project]

            return response
        else:
            self.raise_error('403')

    def get_issue(self, flag, target, id=None):
        if not flag:
            response = {}
            response['expand'] = 'names,schema'
            response['startAt'] = 0
            response['maxResults'] = 50
            response['total'] = 0
            response['issues'] = []

            if not id:
                task_name = target.replace('search?jql=project%%3D\'%s\'%%20AND%%20summary~' % self.project_key, '')
            else:
                task_name = id

            task_name = task_name.replace('\'','')

            if self.get_alm_task(task_name):
                status_id = self.get_alm_task('%s:status' % task_name)
                response['issues'].append(self.generate_issue(task_name, self.get_alm_task(task_name), status_id))
                response['total'] = 1

            return response
        else:
            self.raise_error('400')

    def update_status(self, flag, id, method, data):
        if not flag and method == 'GET':
            response = {"expand":"transitions"}
            transitions = []
            transitions.append(self.generate_transition(1))
            transitions.append(self.generate_transition(2))
            transitions.append(self.generate_transition(3))
            transitions.append(self.generate_transition(4))
            response['transitions'] = transitions
            
            return response
        elif not flag and data and method == 'POST':
            transition_id = data['transition']['id']
            id = id.split('-')[1]

            if not self.get_alm_task('T%s' % id):
                self.add_alm_task('T%s' % id, id)

            self.update_alm_task('T%s:status' % id, int(transition_id) + 1)
            return None
        else:
            self.raise_error(flag)

    def post_issue(self, flag, data):
        if not flag and data:
            # Get title
            if data.get('fields') and data.get('fields').get('summary'):
                task_name = data.get('fields').get('summary')
            elif data.get('summary'):
                task_name = data.get('summary')
                
            if task_name:
                task_name = task_name.partition(':')[0]
                task_id = task_name.split('T')[1]
                self.add_alm_task(task_name, task_id)
                response = {}
                response['id'] = task_id
                response['key'] = '%s-%s' % (self.project_key, 1)
                response['self'] = '%s/issue/%s' % (self.api_url, task_id)

                return response

        self.raise_error('400', '{"errorMessages":["Missing field"],"errors":{}}')
    
    def post_remote_link(self, flag, data, id):
        if not flag:
            if data and data.get('object') and data.get('object').get('title'):
                task_id = id.split('-')[1]
                response = {}
                response['id'] = task_id
                response['self'] = ('%s/rest/api/issue/%s/remotelink/%s' %
                                   (self.base_url, id, task_id))
                                   
                return response
            else:
                self.raise_error('400', '{"errorMessage":[], "errors":{"title":"missing field"}}')
        else:
            self.raise_error(flag)

    """
       JSON Generator 
    """
    def generate_transition(self, id):
        transition = self.get_json_from_file('transition')
        transition['id'] = '%d' % id
        transition['name'] = self.JIRA_TRANSITION_NAMES[id - 1]
        transition['to']['self'] = "%s/status/%d" % (self.api_url, id)
        transition['to']['iconUrl'] = '%s/images/icons/status%d.gif' % (self.base_url, id)
        transition['to']['name'] = self.JIRA_STATUS_NAMES[id]
        transition['to']['id'] = id

        return transition

    def generate_issue(self, task_name, task_number, status_id):
        if status_id is None:
            status_id = 1
  
        id = task_number
        issue = self.get_json_from_file('issue')
        issue['id'] = '%s' % id
        issue['self'] = '%s/issue/%s' % (self.api_url, id)
        issue['key'] = '%s-%s' % (self.project_key, task_number)
        fields = issue['fields']
        fields['issuetype'] = self.generate_issue_type(1)
        fields['reporter'] = self.generate_user()
        fields['priority'] = self.generate_priority(1)
        fields['status'] = self.generate_status(status_id)
        fields['assignee'] = self.generate_user()
        fields['project'] = self.generate_project()
        self.add_alm_task(task_name, id)

        return issue

    def generate_status(self, id):
        status_name = self.JIRA_STATUS_NAMES[id - 1]
        status = {}
        status['self'] = '%s/status/%s' % (self.api_url, id)
        status['description'] = 'Issue description'
        status['iconUrl'] = '%s/images/icons/status_%s.gif' % (self.base_url, status_name)
        status['name'] = status_name
        status['id'] = '%s' % id

        return status

    def generate_priority(self, id):
        priority_name = self.JIRA_PRIORITY_NAMES[id - 1]
        priority = self.get_json_from_file('priority')
        priority['self'] = '%s/priority/%s' % (self.api_url, id)
        priority['iconUrl'] = ('%s/images/icons/priority_%s.gif' % 
                              (self.base_url, priority_name))
        priority['name'] = priority_name
        priority['id'] = id

        return priority

    def generate_user(self):
        return self.get_json_from_file('user')

    def generate_project(self):
        response = self.get_json_from_file('project')
        response['self'] = '%s/project/%s' % (self.api_url, self.project_key)
        response['id'] = self.PROJECT_ID
        response['key'] = self.project_key
        response['name'] = self.project_name
        
        return response

    def generate_issue_type(self, id):
        issueType_name = self.JIRA_ISSUE_TYPES[int(id) - 1]
        issueType = self.get_json_from_file('issue_type')
        issueType['self'] = '%s/issueType/%s' % (self.api_url, id)
        issueType['id'] = id
        issueType['description'] = 'Issue type %s, %s' % (id, issueType_name)
        issueType['iconUrl'] = '%s/images/icons/%s.gif' % (self.base_url, self.urlencode_str(issueType_name))
        issueType['name'] = issueType_name
                            
        if issueType_name == 'Sub-task':
            issueType['subTask'] = True

        return issueType