# NOTE: Before running ensure that the options are set properly in the
#       configuration file

import sys, os, unittest
from urllib2 import HTTPError
from json import JSONEncoder
from mock import patch, MagicMock
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))))

from sdetools.alm_integration.tests.alm_plugin_test_base import AlmPluginTestBase
from sdetools.modules.sync_jira.jira_plugin import JIRAConnector
from sdetools.sdelib.conf_mgr import Config
from sdetools.sdelib.restclient import URLRequest, APIFormatError
from sdetools.modules.sync_jira.jira_rest import APIError
from jira_response_generator import JiraResponseGenerator
from sdetools.modules.sync_jira.jira_rest import JIRARestAPI
from sdetools.modules.sync_jira.jira_soap import JIRASoapAPI
from sdetools.extlib.SOAPpy.Types import faultType
from functools import partial

CONF_FILE_LOCATION = 'test_settings.conf'
MOCK_FLAG = None
JIRA_RESPONSE_GENERATOR = None

def mock_call_api(self, target, method=URLRequest.GET, args=None, call_headers={}):
    try:
        return JIRA_RESPONSE_GENERATOR.get_response(target, MOCK_FLAG, args, method)
    except HTTPError, err:
        # Re-raise with more info
        err.url = '%s/%s' % (err.url, target)
        err.headers = call_headers
        raise APIError(err)


class JiraBaseCase(AlmPluginTestBase):
    @classmethod
    def setUpClass(self):
        PATH_TO_JIRA_CONNECTOR = 'sdetools.modules.sync_jira.jira_plugin'
        super(JiraBaseCase, self).initTest(PATH_TO_JIRA_CONNECTOR)
        self.config.add_custom_option('jira_version', 'Version of JIRA [e.g. 4.3.3, 5, or 6.0]', default='6')
        conf_path = os.path.abspath('%s\%s' % (os.path.dirname(os.path.realpath(__file__)), CONF_FILE_LOCATION))                       
        self.tac = JIRAConnector(self.config, JIRARestAPI(self.config))
        Config.parse_config_file(self.config, conf_path)

        global JIRA_RESPONSE_GENERATOR
        JIRA_RESPONSE_GENERATOR = JiraResponseGenerator(self.config['alm_server'],
                                                        self.config['alm_project'],
                                                        self.config['alm_project_version'],
                                                        self.config['alm_user']) 
                                                        
    def setUp(self):
        super(JiraBaseCase, self).setUp()

    def tearDown(self):
        super(JiraBaseCase, self).tearDown()
        global MOCK_FLAG
        MOCK_FLAG = None
        JIRA_RESPONSE_GENERATOR.clear_alm_tasks()

  
class TestJiraAPI5Case(JiraBaseCase, unittest.TestCase):

    @classmethod
    def setUpClass(self):
        super(TestJiraAPI5Case, self).setUpClass()
        self.config.jira_api_ver = 5
        self.tac.initialize()

        patch('sdetools.modules.sync_jira.jira_rest.RESTBase.call_api', mock_call_api).start()

    def test_sde(self):
        """[SDE] Test mocked functions """
        # Assert mock connect doesn't throw error
        self.tac.sde_connect()
        # Test connection status
        self.assertTrue(self.tac.is_sde_connected())
        # Test SDE get all tasks
        tasklist = self.tac.sde_get_tasks()
        self.assertTrue(tasklist)
        for task in tasklist:
            self.assertTrue(task.has_key('status'))
            self.assertTrue(task.has_key('timestamp'))
            self.assertTrue(task.has_key('phase'))
            self.assertTrue(task.has_key('id'))
            self.assertTrue(task.has_key('priority'))
            self.assertTrue(task.has_key('note_count'))
        # Test SDE get single task
        task = self.tac.sde_get_task('1000-T1')
        self.assertTrue(task)
        # Assert update status doesn't throw error
        self.tac.sde_update_task_status('task', 'status')
        # Test SDE get content
        self.assertEqual(self.tac.sde_get_task_content('task'), 'Task content')
   
    def test_failures(self):
        """[JIRA api5] Test using MOCK_FLAG to force-fail REST API calls"""
        global MOCK_FLAG
        MOCK_FLAG = '401'
        self.assertRaises(APIError, self.tac.alm_plugin.call_api, 'project')
        self.assertRaises(APIError, self.tac.alm_plugin.call_api, 'project/%s/versions' % self.config['alm_project'])
        self.assertRaises(APIError, self.tac.alm_plugin.call_api, 'issue/createmeta')
        self.assertFalse(self.tac.alm_plugin.call_api('issuetype'))     # Returns empty list
        self.assertRaises(APIError, self.tac.alm_plugin.call_api, 'search?jql=project%%3D\'%s\'%%20AND%%20summary~\'T10\'' % self.config['alm_project'])
        self.assertRaises(APIError, self.tac.alm_plugin.call_api, 'issue/%s-10/remotelink' % self.config['alm_project'])
        self.assertRaises(APIError, self.tac.alm_plugin.call_api, 'issue')
        self.assertRaises(APIError, self.tac.alm_plugin.call_api, 'issue/%s-10.*/transitions' % self.config['alm_project'])
        
class MockSoapProxy():
    def __init__(self, wsdlsource, config=Config, **kw ):
        pass
        
    def __getattr__(self, name):
        return partial(self._getResponse, name, MOCK_FLAG)

    def _getResponse(self, *args, **keywords):
        return JIRA_RESPONSE_GENERATOR.get_proxy_response(args)


class TestJiraAPI4Case(JiraBaseCase, unittest.TestCase):
    @classmethod
    def setUpClass(self):
        super(TestJiraAPI4Case, self).setUpClass()
        self.tac.alm_plugin = JIRASoapAPI(self.config)
        self.config.jira_api_ver = 4
        self.tac.initialize()

        mock_opener = MagicMock()
        mock_opener.open = lambda x: x
        patch('sdetools.modules.sync_jira.jira_soap.http_req.get_opener', mock_opener).start()
        mock_proxy = MockSoapProxy       
        patch('sdetools.modules.sync_jira.jira_soap.SOAPpy.WSDL.Proxy', mock_proxy).start()
  
    def test_failures(self):
        """[JIRA api4] Test using MOCK_FLAG to force-fail SOAP Proxy calls"""
        global MOCK_FLAG
        MOCK_FLAG = '401'
        self.assertTrue(type(self.tac.alm_plugin.proxy.getProjectByKey('authToken12345')) == faultType)
        self.assertFalse(self.tac.alm_plugin.proxy.getIssueTypes('authToken12345'))
        self.assertTrue(type(self.tac.alm_plugin.proxy.login('authToken12345','user','pass')) == faultType)
        self.assertFalse(self.tac.alm_plugin.proxy.getStatuses('authToken12345'))
        self.assertFalse(self.tac.alm_plugin.proxy.getPriorities('authToken12345'))
        self.assertTrue(type(self.tac.alm_plugin.proxy.getVersions('authToken12345','data')) == faultType)
        self.assertTrue(type(self.tac.alm_plugin.proxy.getFieldsForCreate('authToken12345')) == faultType)
        self.assertFalse(self.tac.alm_plugin.proxy.getIssuesFromJqlSearch('authToken12345','data'))
        self.assertTrue(type(self.tac.alm_plugin.proxy.createIssue('authToken12345','data')) == faultType)
        self.assertTrue(type(self.tac.alm_plugin.proxy.updateIssue('authToken12345','data')) == faultType)
        self.assertTrue(type(self.tac.alm_plugin.proxy.getAvailableActions('authToken12345')) == faultType)
        self.assertTrue(type(self.tac.alm_plugin.proxy.progressWorkflowAction('authToken12345','data','data')) == faultType)
     