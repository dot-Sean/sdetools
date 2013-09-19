# NOTE: Before running ensure that the options are set properly in the
#       configuration file

import sys, os, unittest
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))))

from sdetools.alm_integration.tests.alm_plugin_test_helper import AlmPluginTestHelper
from sdetools.sdelib.conf_mgr import Config
from sdetools.sdelib.mod_mgr import ReturnChannel
from sdetools.sdelib.interactive_plugin import PlugInExperience
from sdetools.modules.sync_jira.jira_plugin import JIRAConnector

from mock import patch
from sdetools.sdelib.restclient import URLRequest, APIFormatError
from sdetools.alm_integration.alm_plugin_base import AlmException
from sdetools.modules.sync_jira.jira_rest import APIError
def mock_call_api(self, target, method=URLRequest.GET, args=None, call_headers={}):
    if target == 'project':
        return '''[
                    {
                        "self": "http://www.example.com/jira/rest/api/2/project/TEST",
                        "id": "10000",
                        "key": "TEST",
                        "name": "Test-Project",
                        "avatarUrls": {
                            "24x24": "http://www.example.com/jira/secure/projectavatar?size=small&pid=10000",
                            "16x16": "http://www.example.com/jira/secure/projectavatar?size=xsmall&pid=10000",
                            "32x32": "http://www.example.com/jira/secure/projectavatar?size=medium&pid=10000",
                            "48x48": "http://www.example.com/jira/secure/projectavatar?size=large&pid=10000"
                        }
                    }
                ]'''
    elif target == "issuetype":
        return '''[{"self":"http://jira-server:5000/rest/api/2/issuetype/4",
                  "id":"4",
                  "description":"An improvement or enhancement to an existing feature or task.",
                  "iconUrl":"http://jira-server:5000/images/icons/improvement.gif",
                  "name":"Improvement",
                  "subtask":false},
                  {"self":"http://jira-server:5000/rest/api/2/issuetype/3",
                  "id":"3",
                  "description":"A task that needs to be done.",
                  "iconUrl":"http://jira-server:5000/images/icons/task.gif",
                  "name":"Task",
                  "subtask":false},
                  {"self":"http://jira-server:5000/rest/api/2/issuetype/5",
                  "id":"5",
                  "description":"The sub-task of the issue",
                  "iconUrl":"http://jira-server:5000/images/icons/issuetypes/subtask_alternate.png",
                  "name":"Sub-task","subtask":true},
                  {"self":"http://jira-server:5000/rest/api/2/issuetype/1",
                  "id":"1",
                  "description":"A problem which impairs or prevents the functions of the product.",
                  "iconUrl":"http://jira-server:5000/images/icons/bug.gif",
                  "name":"Bug",
                  "subtask":false},
                  {"self":"http://jira-server:5000/rest/api/2/issuetype/2",
                  "id":"2",
                  "description":"A new feature of the product, which has yet to be developed.",
                  "iconUrl":"http://jira-server:5000/images/icons/newfeature.gif",
                  "name":"New Feature",
                  "subtask":false}]'''
    elif target == "search?jql=project%%3D'TEST'%%20AND%%20summary~'task1'":
        return '''{"expand":"names,schema",
                   "startAt":0,
                   "maxResults":50,
                   "total":1,
                   "issues":[{"expand":"editmeta,renderedFields,transitions,changelog,operations",
                              "id":"10133",
                              "self":"http://jira-server:5000/rest/api/2/issue/10133",
                              "key":"TEST-1",
                              "fields":{"summary":"T1: Test Task",
                                        "progress":{"progress":0,"total":0},
                                        "issuetype":{"self":"http://jira-server:5000/rest/api/2/issuetype/1",
                                                     "id":"1",
                                                     "description":"A problem which impairs or prevents the functions of the product.",
                                                     "iconUrl":"http://jira-server:5000/images/icons/bug.gif",
                                                     "name":"Bug",
                                                     "subtask":false
                                                     },
                                        "votes":{"self":"http://jira-server:5000/rest/api/2/issue/TEST-1/votes",
                                                 "votes":0,
                                                 "hasVoted":false
                                                 },
                                        "resolution":null,
                                        "fixVersions":[],
                                        "resolutiondate":null,
                                        "timespent":null,
                                        "reporter":{"self":"http://jira-server:5000/rest/api/2/user?username=username",
                                                    "name":"test",
                                                    "emailAddress":"test+user@sdelements.com",
                                                    "avatarUrls":{
                                                                "16x16":"http://jira-server:5000/secure/useravatar?size=small&avatarId=10122","48x48":"http://jira-server:5000/secure/useravatar?avatarId=10122"
                                                                 },
                                                    "displayName":"Test User,
                                                    "active":true
                                                    },
                                        "aggregatetimeoriginalestimate":null,
                                        "updated":"2013-09-04T19:34:14.000+0000",
                                        "created":"2013-09-04T19:34:14.000+0000",
                                        "description":"Task description",
                                        "priority":{"self":"http://jira-server:5000/rest/api/2/priority/2",
                                                    "iconUrl":"http://jira-server:5000/images/icons/priority_critical.gif",
                                                    "name":"Critical","id":"2"
                                                    },
                                        "duedate":null,
                                        "issuelinks":[],
                                        "watches":{"self":"http://jira-server:5000/rest/api/2/issue/TEST-5/watchers",
                                                   "watchCount":1,
                                                   "isWatching":true
                                                   },
                                        "subtasks":[],
                                        "status":{"self":"http://jira-server:5000/rest/api/2/status/1",
                                                  "description":"The issue is open and ready for the assignee to start work on it.",
                                                  "iconUrl":"http://jira-server:5000/images/icons/status_open.gif",
                                                  "name":"Open",
                                                  "id":"1"
                                                  },
                                        "labels":["SD-Elements"],
                                        "assignee":{"self":"http://jira-server:5000/rest/api/2/user?username=username",
                                                    "name":"test",
                                                    "emailAddress":"test+user@sdelements.com",
                                                    "avatarUrls":{"16x16":"http://jira-server:5000/secure/useravatar?size=small&avatarId=10122",
                                                                  "48x48":"http://jira-server:5000/secure/useravatar?avatarId=10122"
                                                                  },
                                                    "displayName":"Test User",
                                                    "active":true
                                                    },
                                        "workratio":-1,
                                        "aggregatetimeestimate":null,
                                        "project":{"self":"http://jira-server:5000/rest/api/2/project/KTES",
                                                   "id":"10000",
                                                   "key":"TEST",
                                                   "name":"Test-Project",
                                                   "avatarUrls":{"16x16":"http://jira-server:5000/secure/projectavatar?size=small&pid=10000&avatarId=10011",
                                                                 "48x48":"http://jira-server:5000/secure/projectavatar?pid=10000&avatarId=10011"
                                                                 }
                                                    },
                                        "versions":[],
                                        "environment":null,
                                        "timeestimate":null,
                                        "aggregateprogress":{"progress":0,
                                                             "total":0
                                                             },
                                        "lastViewed":null,
                                        "components":[],
                                        "timeoriginalestimate":null,
                                        "aggregatetimespent":null
                                        }
                                    }
                        ]
                    }'''
    else:
        raise APIError('Error calling API')

patch('sdetools.modules.sync_jira.jira_rest.RESTBase.call_api', mock_call_api).start()
from sdetools.modules.sync_jira.jira_rest import JIRARestAPI

CONF_FILE_LOCATION = 'test_settings.conf'
def stdout_callback(obj):
    print obj
    
class TestJiraCase(AlmPluginTestHelper, unittest.TestCase):

    def setUp(self):
        conf_path = os.path.abspath('%s\%s' % (os.path.dirname(os.path.realpath(__file__)), CONF_FILE_LOCATION))
        ret_chn = ReturnChannel(stdout_callback, {})
        config = Config('', '', ret_chn, 'import')
        self.tac = JIRAConnector(config, JIRARestAPI(config))
        Config.parse_config_file(config, conf_path)
        super(TestJiraCase, self).setUp()
    
    def test_connect(self):
        # Assert Server Success
        self.tac.alm_plugin.connect_server
        # Assert Project Success
        self.tac.alm_plugin.connect_project
        # Assert Error
        self.assertRaises(APIError, self.tac.alm_plugin.call_api, '')

    def test_parse_result(self):
        # Assert bad json error checking
        result = "crappy json"
        self.assertRaises(APIFormatError, self.tac.alm_plugin.parse_response, result)
        # Assert successful json parsing
        result = self.tac.alm_plugin.call_api('project')
        json = self.tac.alm_plugin.parse_response(result)
        self.assertTrue(json[0].get('self'))
        self.assertTrue(json[0].get('id'))
        self.assertTrue(json[0].get('key'))
        self.assertTrue(json[0].get('name'))
        self.assertTrue(json[0].get('avatarUrls'))
        self.assertTrue(json[0].get('avatarUrls').get('24x24'))
        self.assertFalse(json[0].get('non-existant-key'))

if __name__ == "__main__":
    unittest.main()
