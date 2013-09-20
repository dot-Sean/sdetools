from urllib2 import HTTPError
import urllib
from mock import MagicMock
import re

class JiraResponseGenerator():
    api_url = 'rest/api/2'
    PROJECT_ID = '10000'
    JIRA_ISSUE_TYPES = ["Bug", "New Feature", "Task", "Improvement", "Sub-task"]
    JIRA_ISSUE_DEFAULT_ID_BASE = 10130
    JIRA_ISSUE_ID_BASE = 10130
    JIRA_PRIORITY_NAMES = ['Blocker']
    JIRA_STATUS_NAMES = ['Open', 'In Progress', 'Resolved', 'Closed', 'Reopened']
    JIRA_TRANSITION_NAMES = ['Start Progress', 'Resolve Issue', 'Close Issue']
    project_name = 'Test Project'
    JIRA_TASKS = {}
    # Not specifying a result field will automatically assume success
    # for all method types.
    # Example: [{'target'='api_target_url','result'=[{'method'='get','result_type'='pass'}]}]

    def add_jira_task(self, task_name, id):
        self.JIRA_TASKS[task_name] = id

    def clear_jira_tasks(self):
        self.JIRA_ISSUE_ID_BASE = self.JIRA_ISSUE_DEFAULT_ID_BASE
        self.JIRA_TASKS = {}

    def urlencode_str(self, instr):
        return urllib.urlencode({'a':instr})[2:]

    def __init__(self, host, project_key, project_version, username, protocol='http'):
        self.base_url = '%s://%s' % (protocol, host)
        self.api_url = '%s/%s' % (self.base_url, self.api_url)
        self.project_key = project_key
        self.project_version = project_version
        self.username = username
        
    JIRA_API_CALL_RESULT_MAPPING = [{'target':'project'},
                                    {'target':'project/%s/versions'},
                                    {'target':'issue/createmeta'},
                                    {'target':'issuetype'},
                                    {'target':'search?jql=project%%3D\'%s\'%%20AND%%20summary~\'%s\''},
                                    {'target':'issue/%s'},
                                    {'target':'issue'},
                                    {'target':'issue/%s/transitions'}]
    def get_response(self, target, flag, data, method):
        print target
        print data
        print method
        if target == 'project':
            return self.get_projects(flag)
        elif target == 'issuetype':
            return self.get_issue_types(flag)
        elif target == 'project/%s/versions' % self.project_key:
            return self.get_project_versions(flag)
        elif target == 'issue/createmeta':
            return self.get_create_meta(flag)
        elif 'search?jql=project%%3D\'%s\'%%20AND%%20summary~' % self.project_key in target:
            return self.get_issue(flag, target)
        elif target == 'issue':
            return self.post_issue(flag, data)
        elif re.match('issue/%s-\S.*/remotelink$' % self.project_key, target):
            id = target.split('/')[1]
            return self.post_remote_link(flag, data, id)
        elif re.match('issue/%s-\S.*/transitions$' % self.project_key, target):
            id = target.split('/')[1]
            return self.get_transitions(flag, id)

        fp_mock = MagicMock()
        fp_mock.read.return_value = 'Invalid URL'
        raise HTTPError('%s' % self.api_url, '404', 'Invalid URL', '', fp_mock)

    """
       Response functions 
    """
    def get_projects(self, flag):
        if not flag:
            response = []
            response.append(self.generate_project())
            
            return response
        else:
            fp_mock = MagicMock()
            fp_mock.read.return_value = 'Failed to locate projects'
            raise HTTPError('%s' % self.api_url, '500', 'Error finding projects', '', fp_mock)

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
                version = {}
                version['self'] = "%s/version/%s" % (self.api_url, self.project_version)
                version['id'] = self.project_version
                version['description'] = "Test version"
                version['archived'] = False
                version['released'] = True
                version['releaseDate'] = "2010-07-06"
                version['overdue'] = True
                version['userReleaseDate'] = "6/Jul/2010"
                response.append(version)

            return response
        else:
            fp_mock = MagicMock()
            fp_mock.read.return_value = 'The project is not found, or the calling user does not have permission to view it.'
            raise HTTPError('%s' % self.api_url, '404', 'The project is not found, or the calling user does not have permission to view it.', '', fp_mock)

    def get_create_meta(self, flag):
        if not flag:
            response = {}
            response['expands'] = 'projects'
            _project = self.generate_project()
            _project['issuetypes'] = self.get_issue_types(flag)
            response['projects'] = [_project]

            return response
        else:
            fp_mock = MagicMock()
            fp_mock.read.return_value = 'No permission'
            raise HTTPError('%s' % self.api_url, '403', 'No permission', '', fp_mock)

    def get_issue(self, flag, target):
        if not flag:
            response = {}
            response['expand'] = 'names,schema'
            response['startAt'] = 0
            response['maxResults'] = 50
            response['total'] = len(self.JIRA_TASKS)
            response['issues'] = []
            task_name = target.replace('search?jql=project%%3D\'%s\'%%20AND%%20summary~' % self.project_key, '')
            task_name = task_name.replace('\'','')

            if self.JIRA_TASKS.get(task_name):
                response['issues'].append(self.generate_issue(task_name, self.JIRA_TASKS.get(task_name)))

            return response
        else:
            fp_mock = MagicMock()
            fp_mock.read.return_value = 'Problem with query'
            raise HTTPError('%s' % self.api_url, '400', 'Problem with query', '', fp_mock)

    def get_transitions(self, flag, id):
        response = {"expand":"transitions"}
        transitions = []
        transitions.append(self.generate_transition(1))
        transitions.append(self.generate_transition(2))
        transitions.append(self.generate_transition(3))
        response['transitions'] = transitions

        return response

    def post_issue(self, flag, data):
        if not flag and data:
            if data.get('fields') and data.get('fields').get('summary'):
                task_name = data.get('fields').get('summary').partition(':')[0]
                self.add_jira_task(task_name, self.JIRA_ISSUE_ID_BASE)
                response = {}
                response['id'] = self.JIRA_ISSUE_ID_BASE
                response['key'] = '%s-%s' % (self.project_key, 1)
                response['self'] = '%s/issue/%s' % (self.api_url, self.JIRA_ISSUE_ID_BASE)
                self.JIRA_ISSUE_ID_BASE = self.JIRA_ISSUE_ID_BASE + 1

                return response

        fp_mock = MagicMock()
        fp_mock.read.return_value = '{"errorMessages":["Missing field"],"errors":{}}'
        raise HTTPError('%s' % self.api_url, '400', 'Problem with query', '', fp_mock)
    
    def post_remote_link(self, flag, data, id):
        if not flag and data:
            if data.get('object') and data.get('object').get('title'):
                response = {}
                response['id'] = self.JIRA_ISSUE_ID_BASE
                response['self'] = ('%s/rest/api/issue/%s/remotelink/%s' %
                                   (self.base_url, id, self.JIRA_ISSUE_ID_BASE))
                                   
                return response

        fp_mock = MagicMock()
        fp_mock.read.return_value = '{"errorMessage":[], "errors":{"title":"missing field"}}'

        if flag == '401':
            fp_mock.read.return_value = 'Not authenticated'
        elif flag == '403':
            fp_mock.read.return_value = 'No permission'

        raise HTTPError('%s' % self.api_url, flag, 'Invalid Input', '', fp_mock)

    """
       JSON Generator 
    """
    def generate_transition(self, id):
        transition = {}
        transition['id'] = '%d' % id
        transition['name'] = self.JIRA_TRANSITION_NAMES[id - 1]
        transition['to'] = {"self":"%s/status/%d" % (self.api_url, id + 1),
                            "description":"Description",
                            "iconUrl":'%s/images/icons/status%d.gif' % (self.base_url, id + 1),
                            "name":self.JIRA_STATUS_NAMES[id],
                            "id": id + 1}
        field_summary = {
                            "required": False,
                            "schema": {
                                "type": "array",
                                "items": "option",
                                "custom": "com.atlassian.jira.plugin.system.customfieldtypes:multiselect",
                                "customId": 10001
                            },
                            "name": "My Multi Select",
                            "operations": [
                                "set",
                                "add"
                            ],
                            "allowedValues": [
                                "red",
                                "blue"
                            ]
                        }
        transition['fields'] = {"summary":field_summary}

        return transition

    def generate_issue(self, task_name, task_number):
        id = task_number
        issue = {}
        issue['expand'] = 'editmeta,renderedFields,transitions,changelog,operations'
        issue['id'] = '%s' % id
        issue['self'] = '%s/issue/%s' % (self.api_url, id)
        issue['key'] = '%s-%s' % (self.project_key, task_number)
        fields = {}
        fields['summary'] = 'Issue summary'
        fields['progress'] = {"progress":0,"total":0}
        fields['issuetype'] = self.generate_issue_type(1)
        fields['votes'] = {"self":'%s/issue/%s/votes' % (self.api_url, issue['key']),
                           "votes":0,
                           "hasVoted":False}
        fields['resolution'] = None
        fields['fixVersions'] = []
        fields['resolutiondate'] = None
        fields['timespent'] = None
        fields['reporter'] = self.generate_user()
        fields['aggregatetimeoriginalestimate'] = None
        fields['updated']  = '2013-09-04T19:34:03.000+0000'
        fields['created'] = '2013-09-04T19:34:03.000+0000'
        fields['description'] = 'Issue Description'
        fields['priority'] = self.generate_priority(1)
        fields['duedate"'] = None
        fields['issuelinks'] = []
        fields["watches"] = {"self":"%s/issue/%s/watchers" % (self.api_url, issue['key']),
                             "watchCount":1,"isWatching":True}
        fields["subtasks"] = []
        fields['status'] = self.generate_status(1)
        fields["labels"] = ["SD-Elements"]
        fields['assignee'] = self.generate_user()
        fields["workratio"] = -1
        fields['aggregatetimeestimate'] = None
        fields['project'] = self.generate_project()
        fields["versions"] = []
        fields["environment"] = None
        fields["timeestimate"] = None
        fields["aggregateprogress"] = {"progress":0,"total":0}
        fields["lastViewed"] = "2013-09-10T17:54:05.527+0000"
        fields["components"] = []
        fields["timeoriginalestimate"] = None
        fields["aggregatetimespent"] = None
        issue['fields'] = fields
        self.add_jira_task(task_name, id)

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
        priority = {}
        priority['self'] = '%s/priority/%s' % (self.api_url, id)
        priority['iconUrl'] = ('%s/images/icons/priority_%s.gif' % 
                              (self.base_url, priority_name))
        priority['name'] = priority_name
        priority['id'] = id
        
        return priority

    def generate_user(self):
        user = {}
        user['self'] = '%s/user?username=%s' % (self.api_url, self.username)
        user['name'] = self.username
        user['emailAddress'] = '%s+test@sdelements.com' % self.username
        user['avatarUrls'] = {"16x16":self.generate_user_avatar_url('16x16')}
        user['displayName'] = self.username
        user['active'] = True

        return user

    def generate_project(self):
        project = {}
        project['self'] = '%s/project/%s' % (self.api_url, self.project_key)
        project['id'] = self.PROJECT_ID
        project['key'] = self.project_key
        project['name'] = self.project_name
        avatarUrls = {}
        avatarUrls['24x24'] = self.generate_project_avatar_url('24x24')
        avatarUrls['16x16'] = self.generate_project_avatar_url('16x16')
        avatarUrls['32x32'] = self.generate_project_avatar_url('32x32')
        avatarUrls['48x48'] = self.generate_project_avatar_url('48x48')
        project['avatarUrls'] = avatarUrls
        
        return project

    def generate_issue_type(self, id):
        issueType_name = self.JIRA_ISSUE_TYPES[int(id) - 1]
        issueType = {}
        issueType['self'] = '%s/issueType/%s' % (self.api_url, id)
        issueType['id'] = id
        issueType['description'] = 'Issue type %s, %s' % (id, issueType_name)
        issueType['iconUrl'] = '%s/images/icons/%s.gif' % (self.base_url, self.urlencode_str(issueType_name))
        issueType['name'] = issueType_name
        _issueType = {
                      "required": True,
                      "name": "Issue Type",
                      "operations": ["set"]
                     }
        issueType["fields"] = {"issuetype":_issueType}
                            
        if issueType_name == 'Sub-task':
            issueType['subTask'] = True
        else:
            issueType['subTask'] = False

        return issueType

    def generate_user_avatar_url(self, size):
        if size == '24x24':
            _size = 'small'
        elif size == '16x16':
            _size = 'xsmall'
        elif size == '32x32':
            _size = 'medium'
        elif size == '48x48':
            _size = 'large'

        return '%s/secure/useravatar?size=%s&avatarId=10122' % (self.base_url, _size)

    def generate_project_avatar_url(self, size):
        if size == '24x24':
            _size = 'small'
        elif size == '16x16':
            _size = 'xsmall'
        elif size == '32x32':
            _size = 'medium'
        elif size == '48x48':
            _size = 'large'

        return '%s/secure/projectavatar?size=%s&pid=%s' % (self.base_url, _size, self.PROJECT_ID)