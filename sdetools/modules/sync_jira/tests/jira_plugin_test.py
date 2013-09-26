# NOTE: Before running ensure that the options are set properly in the
#       configuration file
import sys
import os
import unittest

from mock import patch, MagicMock
from functools import partial
from jira_response_generator import JiraResponseGenerator

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))))
from sdetools.alm_integration.tests.alm_plugin_test_base import AlmPluginTestBase
from sdetools.extlib.SOAPpy.Types import faultType
from sdetools.modules.sync_jira.jira_plugin import JIRAConnector
from sdetools.modules.sync_jira.jira_rest import JIRARestAPI, APIError
from sdetools.modules.sync_jira.jira_soap import JIRASoapAPI
from sdetools.sdelib.conf_mgr import Config
import sdetools.alm_integration.tests.alm_mock_response

CONF_FILE_LOCATION = 'test_settings.conf'
MOCK_RESPONSE = sdetools.alm_integration.tests.alm_mock_response


class JiraBaseCase(AlmPluginTestBase):
    @classmethod
    def setUpClass(cls):
        path_to_jira_connector = 'sdetools.modules.sync_jira.jira_plugin'
        current_dir = os.path.dirname(os.path.realpath(__file__))
        conf_path = os.path.join(current_dir, CONF_FILE_LOCATION)
        super(JiraBaseCase, cls).setUpClass(path_to_jira_connector, conf_path)

    @classmethod
    def init_alm_connector(cls):
        cls.config.add_custom_option('jira_version', 'Version of JIRA [e.g. 4.3.3, 5, or 6.0]', default='6')
        cls.tac = JIRAConnector(cls.config, JIRARestAPI(cls.config))

    @classmethod
    def init_response_generator(cls):
        response_generator = JiraResponseGenerator(cls.config['alm_server'],
                                                   cls.config['alm_project'],
                                                   cls.config['alm_project_version'],
                                                   cls.config['alm_user'])

        path_to_rest_plugin = 'sdetools.modules.sync_jira.jira_rest'
        MOCK_RESPONSE.patch_call_rest_api(response_generator, path_to_rest_plugin)

    def setUp(self):
        super(JiraBaseCase, self).setUp()

    def tearDown(self):
        super(JiraBaseCase, self).tearDown()


class TestJiraAPI6Case(JiraBaseCase, unittest.TestCase):
    def test_failures(self):
        """[JIRA api6] Test using MOCK_FLAG to force-fail REST API calls"""
        MOCK_RESPONSE.set_mock_flag('401')
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
        return partial(self.get_response, name, MOCK_RESPONSE.mock_flag)

    @staticmethod
    def get_response(*args, **keywords):
        return MOCK_RESPONSE.get_response_generator().get_proxy_response(args)


class TestJiraAPI4Case(JiraBaseCase, unittest.TestCase):
    @classmethod
    def init_alm_connector(cls):
        super(TestJiraAPI4Case, cls).init_alm_connector()
        cls.tac.alm_plugin = JIRASoapAPI(cls.config)
        cls.config.jira_api_ver = 4

    @classmethod
    def init_response_generator(cls):
        super(TestJiraAPI4Case, cls).init_response_generator()
        mock_opener = MagicMock()
        mock_opener.open = lambda x: x
        patch('sdetools.modules.sync_jira.jira_soap.http_req.get_opener', mock_opener).start()
        mock_proxy = MockSoapProxy
        patch('sdetools.modules.sync_jira.jira_soap.SOAPpy.WSDL.Proxy', mock_proxy).start()

    def test_failures(self):
        """[JIRA api4] Test using MOCK_FLAG to force-fail SOAP Proxy calls"""
        MOCK_RESPONSE.set_mock_flag('401')
        self.assertTrue(type(self.tac.alm_plugin.proxy.getProjectByKey('authToken12345')) == faultType)
        self.assertFalse(self.tac.alm_plugin.proxy.getIssueTypes('authToken12345'))
        self.assertTrue(type(self.tac.alm_plugin.proxy.login('authToken12345', 'user', 'pass')) == faultType)
        self.assertFalse(self.tac.alm_plugin.proxy.getStatuses('authToken12345'))
        self.assertFalse(self.tac.alm_plugin.proxy.getPriorities('authToken12345'))
        self.assertTrue(type(self.tac.alm_plugin.proxy.getVersions('authToken12345', 'data')) == faultType)
        self.assertTrue(type(self.tac.alm_plugin.proxy.getFieldsForCreate('authToken12345')) == faultType)
        self.assertFalse(self.tac.alm_plugin.proxy.getIssuesFromJqlSearch('authToken12345','data'))
        self.assertTrue(type(self.tac.alm_plugin.proxy.createIssue('authToken12345', 'data')) == faultType)
        self.assertTrue(type(self.tac.alm_plugin.proxy.updateIssue('authToken12345', 'data')) == faultType)
        self.assertTrue(type(self.tac.alm_plugin.proxy.getAvailableActions('authToken12345')) == faultType)
        self.assertTrue(type(self.tac.alm_plugin.proxy.progressWorkflowAction('authToken12345', 'data', 'data')) == faultType)
