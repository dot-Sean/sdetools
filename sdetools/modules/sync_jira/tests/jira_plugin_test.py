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
from sdetools.modules.sync_jira.jira_plugin import JIRAConnector, AlmException
from sdetools.modules.sync_jira.jira_rest import JIRARestAPI
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
    def test_fail_connect_server(self):
        MOCK_RESPONSE.set_mock_flag({'get_projects': '500'})
        self.assert_exception(AlmException, '', 'HTTP Error 500: Server error', self.tac.alm_plugin.connect_server)


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

    def test_fail_connect_server(self):
        MOCK_RESPONSE.set_mock_flag({'login': '401'})
        self.assert_exception(AlmException, '', 'HTTP Error 401', self.tac.alm_plugin.connect_server)

