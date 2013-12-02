# NOTE: Before running ensure that the options are set properly in the
#       configuration file
import unittest

from mock import patch, MagicMock
from functools import partial
from jira_response_generator import JiraResponseGenerator
from sdetools.sdelib.conf_mgr import Config
from sdetools.sdelib.testlib.mock_response import MOCK_ALM_RESPONSE
from sdetools.alm_integration.tests.alm_plugin_test_base import AlmPluginTestBase
from sdetools.modules.sync_jira.jira_plugin import JIRAConnector, AlmException
from sdetools.modules.sync_jira.jira_rest import JIRARestAPI
from sdetools.modules.sync_jira.jira_soap import JIRASoapAPI


class JiraBaseCase(AlmPluginTestBase):
    @classmethod
    def setUpClass(cls):
        alm_classes = [JIRAConnector, JIRARestAPI, JiraResponseGenerator]
        super(JiraBaseCase, cls).setUpClass(alm_classes=alm_classes)

    def pre_parse_config(self):
        self.config.opts.add('jira_version', 'Version of JIRA [e.g. 4.3.3, 5, or 6.0]', default='6')

    def post_parse_config(self):
        api_ver = self.config['jira_version'][:1]
        self.config.jira_api_ver = int(api_ver)

    def test_parsing_alm_task(self):
        result = super(JiraBaseCase, self).test_parsing_alm_task()
        test_task = result[0]
        test_task_result = result[1]

        alm_id = 'TEST-%s' % test_task['id'].split('T')[1]
        result_alm_id = test_task_result.get_alm_id()

        self.assertEqual(result_alm_id, alm_id, 'Expected alm_id %s, got %s' % (alm_id, result_alm_id))

    def test_parse_non_done_status_as_todo(self):
        self.connector.alm_connect()
        test_task = self.mock_sde_response.generate_sde_task()
        self.connector.alm_add_task(test_task)
        test_task_result = self.connector.alm_get_task(test_task)
        test_task_result.status = "Non-done status"

        self.assertEqual(test_task_result.get_status(), "TODO", 'Expected status to default to TODO')

    def test_with_project_version(self):
        self.config['alm_project_version'] = '1.0'
        self.post_parse_config()  # Re-init with project version
        self.init_response_generator()
        self.connector.alm_connect()
        test_task = self.mock_sde_response.generate_sde_task()
        self.connector.alm_add_task(test_task)
        test_task_result = self.connector.alm_get_task(test_task)

        self.assertEqual(test_task_result.versions, ['1.0'])


class TestJiraAPI6Case(JiraBaseCase, unittest.TestCase):
    def test_fail_connect_server(self):
        self.mock_alm_response.set_response_flags({'get_projects': '500'})

        self.assert_exception(AlmException, '', 'HTTP Error 500. Explanation returned: FATAL ERROR: "Server error"', self.connector.alm_plugin.connect_server)

    def test_convert_markdown_for_links(self):
        content = '[https://m1.sdelements.com/library/tasks/T21/](https://m1.sdelements.com/library/tasks/T21/)'
        expected = '[https://m1.sdelements.com/library/tasks/T21/|https://m1.sdelements.com/library/tasks/T21/]'

        self.assert_markdown(content, expected)

    def test_convert_markdown_for_italic_text(self):
        content = '*Italic Text*'
        expected = '_Italic Text_'

        self.assert_markdown(content, expected)

    def test_convert_markdown_for_bold_text(self):
        content = '**Bold Text!**'
        expected = '*Bold Text!*'

        self.assert_markdown(content, expected)

    def test_convert_markdown_for_inline_code(self):
        content = '`print "Hello World!";`'
        expected = '*print "Hello World!";*'

        self.assert_markdown(content, expected)

    def test_custom_fields(self):
        self.config['alm_custom_fields'] = {"Custom Field":"value"}
        self.connector.initialize()
        self.connector.alm_connect()

        self.assertEqual(self.connector.alm_plugin.custom_fields[0]['field'], "customField")
        self.assertEqual(self.connector.alm_plugin.custom_fields[0]['value'], "value")

    def assert_markdown(self, content, expected):
        converted_text = self.connector.convert_markdown_to_alm(content, None)

        self.assertEqual(converted_text, expected, 'Expected %s, got %s' % (expected, converted_text))


class MockSoapProxy():
    def __init__(self, wsdlsource, config=Config, **kw ):
        pass

    def __getattr__(self, name):
        return partial(self.get_response, name, MOCK_ALM_RESPONSE.get_response_flags())

    @staticmethod
    def get_response(*args, **keywords):
        return MOCK_ALM_RESPONSE.get_response_generator().get_proxy_response(args)


class TestJiraAPI4Case(JiraBaseCase, unittest.TestCase):
    def post_parse_config(self):
        self.config['jira_version'] = '4'
        self.config.jira_api_ver = 4
        self.connector.alm_plugin = JIRASoapAPI(self.config)

        mock_opener = MagicMock()
        mock_opener.open = lambda x: x
        patch('sdetools.modules.sync_jira.jira_soap.http_req.get_opener', mock_opener).start()
        mock_proxy = MockSoapProxy
        patch('sdetools.modules.sync_jira.jira_soap.SOAPpy.WSDL.Proxy', mock_proxy).start()

    def test_bad_credentials(self):
        self.mock_alm_response.set_response_flags({'login': '401'})

        self.assert_exception(AlmException, '', 'Unable to login to JIRA. Please check ID, password',
                              self.connector.alm_plugin.connect_server)

    def test_custom_fields(self):
        self.connector.alm_connect()
        self.config['alm_custom_fields'] = {"Custom Field":"value"}
        test_task = self.mock_sde_response.generate_sde_task()
        self.connector.alm_add_task(test_task)
        alm_task = self.connector.alm_get_task(test_task)
        self.config['jira_existing_issue'] = alm_task.get_alm_id()
        self.connector.initialize()
        self.connector.alm_connect()

        self.assertEqual(self.connector.alm_plugin.custom_fields[0]['field'], "customField")
        self.assertEqual(self.connector.alm_plugin.custom_fields[0]['value'], "value")
