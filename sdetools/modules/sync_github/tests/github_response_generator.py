from urllib2 import HTTPError
import urllib
from mock import MagicMock
import re

class TwoWayDict(dict):
    def __len__(self):
        return dict.__len__(self) / 2

    def __setitem__(self, key, value):
        dict.__setitem__(self, key, value)
        dict.__setitem__(self, value, key)

class GitHubResponseGenerator():
    GITHUB_STATUS_NAMES = ['Open', 'Closed']
    GITHUB_TASKS = TwoWayDict()

    def add_github_task(self, task_name, id):
        if not self.GITHUB_TASKS.get(task_name):
            self.GITHUB_TASKS[task_name] = id
            self.GITHUB_TASKS['%s:status' % task_name] = 'open'

    def clear_github_tasks(self):
        self.GITHUB_TASKS = TwoWayDict()

    def urlencode_str(self, instr):
        return urllib.urlencode({'a':instr})[2:]

    def __init__(self, host, repo_org, repo_name, project_milestone, username, protocol='http'):
        self.project_uri = '%s/%s' % (self.urlencode_str(repo_org), self.urlencode_str(repo_name))
        self.api_url = '%s://%s/%s' % (protocol, host, self.project_uri)
        self.project_milestone = project_milestone
        self.username = username
        
    def get_response(self, target, flag, data, method):
        GITHUB_API_TARGETS = {'get_user':'user',
                            'get_repo':'repos/%s',
                            'get_milestones':'repos/%s/milestones',
                            'get_task':'legacy/issues/search/%s',
                            'post_issue':'repos/%s/issues',
                            'update_status':'repos/%s/issues/[0-9]*$'}
        #print method + ' at ' + target + ' with ' 
        #print data

        if target == GITHUB_API_TARGETS['get_user']:
            return self.get_user(flag)
        elif target == GITHUB_API_TARGETS['get_repo'] % self.project_uri:
            return self.get_repo(flag)
        elif target == GITHUB_API_TARGETS['get_milestones'] % self.project_uri:
            return self.get_milestones(flag)
        elif GITHUB_API_TARGETS['get_task'] % self.project_uri in target:
            return self.get_task(flag, target)
        elif target == GITHUB_API_TARGETS['post_issue'] % self.project_uri:
            return self.post_issue(flag, data)
        elif re.match(GITHUB_API_TARGETS['update_status'] % self.project_uri, target):
            return self.update_status(flag, target, data)

        fp_mock = MagicMock()
        fp_mock.read.return_value = 'Invalid URL'
        raise HTTPError('%s' % self.api_url, '404', 'Invalid URL', '', fp_mock)

    """
       Response functions 
    """
    def get_user(self, flag):
        if not flag:
            response = {
                          "login": "test",
                          "id": 1,
                          "avatar_url": "testIcon.gif",
                          "gravatar_id": "somehexcode",
                          "url": "https://api.github.com/users/test",
                          "name": "test user",
                          "company": "SecurityCompass",
                          "email": "test+user@securitycompass.com",
                        }

            return response
        else:
            fp_mock = MagicMock()
            fp_mock.read.return_value = '{"message":"Requires authentication","documentation_url":"http://developer.github.com/v3"}'
            raise HTTPError('%s' % self.api_url, '401', 'Unauthorized user', '', fp_mock)

    def get_repo(self, flag):
        if not flag:
            response = {
                          "id": 1296269,
                          "owner": self.generate_user(),
                          "name": "test repo",
                          "full_name": "testOrg/testRepo",
                          "description": "TestRepo",
                          "url": "https://api.github.com/repos/testOrg/testRepo",
                        }

            return response
        else:
            fp_mock = MagicMock()
            fp_mock.read.return_value = '{"message":"Not found","documentation_url":"http://developer.github.com/v3"}'
            raise HTTPError('%s' % self.api_url, '404', 'Not found', '', fp_mock)

    def get_milestones(self, flag):
        if not flag:
            response = [self.generate_milestone()]

            return response
        else:
            # No result
            return []

    def get_task(self, flag, target):
        ids = target.split('/')
        state = ids[len(ids) - 2]
        task_name = ids[len(ids) - 1]
        task_name = task_name.split(self.urlencode_str(':'))[0]
        if not flag and self.GITHUB_TASKS.get(task_name):
            status = self.GITHUB_TASKS.get('%s:status' % task_name)
            if status == state:
                response = {
                              "issues": [
                                {
                                  "position": 10,
                                  "number": self.GITHUB_TASKS.get(task_name),
                                  "votes": 2,
                                  "created_at": "2010-06-04T23:20:33Z",
                                  "comments": 5,
                                  "body": "Issue body goes here",
                                  "title": "title",
                                  "updated_at": "2010-06-04T23:20:33Z",
                                  "html_url": "link_to_issue",
                                  "user": "test",
                                  "labels": [
                                    "task", "SD Elements"
                                  ],
                                  "state": state
                                }
                              ]
                            }

                return response

        return {"issues": []}
            
    def post_issue(self, flag, data):
        if not flag:
            name = data['title'].split(':')[0]
            id = name.split('T')[1]
            self.add_github_task(name, id)
            response = self.generate_issue(name, id, 'open')

            return response
        else:
            fp_mock = MagicMock()
            fp_mock.read.return_value = '{"message":"Not found","documentation_url":"http://developer.github.com/v3"}'
            raise HTTPError('%s' % self.api_url, '404', 'Not found', '', fp_mock)
            
    def update_status(self, flag, target, data):
        id = target.split('/')[4]
        
        if not flag:
            if self.GITHUB_TASKS.get(id) and data['state']:
                name = self.GITHUB_TASKS.get(id)
                status = data['state']
                response = self.generate_issue(name, id, status)
                self.GITHUB_TASKS['%s:status' % name] = status

                return response
            else:
                fp_mock = MagicMock()
                fp_mock.read.return_value = '{"message":"Not found","documentation_url":"http://developer.github.com/v3"}'
                raise HTTPError('%s' % self.api_url, '404', 'Not found', '', fp_mock)
        else:
            fp_mock = MagicMock()
            fp_mock.read.return_value = '{"message":"Requires authentication","documentation_url":"http://developer.github.com/v3"}'
            raise HTTPError('%s' % self.api_url, '401', 'Unauthorized user', '', fp_mock)
    """
       JSON Generator 
    """
    def generate_issue(self, name, id, status):
        return {
                  "number": id,
                  "state": status,
                  "title": name,
                  "body": "I'm having a problem with this.",
                  "user": self.generate_user(),
                  "labels": [
                    {
                      "url": "https://api.github.com/repos/testOrg/testRepo/task",
                      "name": "task",
                      "color": "f29513"
                    },
                    {
                      "url": "https://api.github.com/repos/testOrg/testRepo/SD%20Elements",
                      "name": "SD Elements",
                      "color": "f29513"
                    }
                  ],
                  "assignee": self.generate_user(),
                  "milestone": self.generate_milestone(),
                  "closed_at": None,
                  "created_at": "2011-04-22T13:33:48Z",
                  "updated_at": "2011-04-22T13:33:48Z"
                }

    def generate_user(self):
        user = {
                  "login": "test",
                  "id": 1,
                  "avatar_url": "testIcon.gif",
                  "gravatar_id": "somehexcode",
                  "url": "https://api.github.com/users/test"
                }

        return user

    def generate_milestone(self):
        milestone = {
                        "url": "%s/milestones/1" % self.api_url,
                        "number": 1,
                        "state": "open",
                        "title": "milestone01",
                        "description": "",
                        "creator": self.generate_user(),
                        "open_issues": 4,
                        "closed_issues": 8,
                        "created_at": "2011-04-10T20:09:31Z",
                        "due_on": None
                    }
         
        return milestone