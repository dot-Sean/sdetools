# NOTE: Before running ensure that the options are set properly in the
#       configuration file
import sys
import os
import unittest
from datetime import datetime
from mock import patch, MagicMock
from functools import partial
from jira_response_generator import JiraResponseGenerator

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))))
import sdetools.alm_integration.tests.alm_mock_response
import sdetools.alm_integration.tests.alm_mock_sde_plugin
from sdetools.alm_integration.tests.alm_plugin_test_base import AlmPluginTestBase
from sdetools.modules.sync_jira.jira_plugin import JIRAConnector, AlmException
from sdetools.modules.sync_jira.jira_rest import JIRARestAPI
from sdetools.modules.sync_jira.jira_soap import JIRASoapAPI
from sdetools.sdelib.conf_mgr import Config

CONF_FILE_LOCATION = 'test_settings.conf'
MOCK_RESPONSE = sdetools.alm_integration.tests.alm_mock_response
MOCK_SDE = sdetools.alm_integration.tests.alm_mock_sde_plugin

class JiraBaseCase(AlmPluginTestBase):
    @classmethod
    def setUpClass(cls):
        path_to_jira_connector = 'sdetools.modules.sync_jira.jira_plugin'
        current_dir = os.path.dirname(os.path.realpath(__file__))
        conf_path = os.path.join(current_dir, CONF_FILE_LOCATION)
        super(JiraBaseCase, cls).setUpClass(path_to_jira_connector, conf_path)

    def init_alm_connector(self):
        self.config.add_custom_option('jira_version', 'Version of JIRA [e.g. 4.3.3, 5, or 6.0]', default='6')
        connector = JIRAConnector(self.config, JIRARestAPI(self.config))
        super(JiraBaseCase, self).init_alm_connector(connector)

    def post_parse_config(self):
        api_ver = self.config['jira_version'][:1]
        self.config.jira_api_ver = int(api_ver)
        response_generator = JiraResponseGenerator(self.config['alm_server'],
                                                   self.config['alm_project'],
                                                   self.config['alm_project_version'],
                                                   self.config['alm_user'])

        path_to_rest_plugin = 'sdetools.modules.sync_jira.jira_rest'
        MOCK_RESPONSE.patch_call_rest_api(response_generator, path_to_rest_plugin)

    def test_parsing_alm_task(self):
        result = super(JiraBaseCase, self).test_parsing_alm_task()
        test_task = result[0]
        test_task_result = result[1]

        task_id = test_task['title'].split(':')[0]
        alm_id = 'TEST-%s' % test_task['id'].split('T')[1]
        alm_status = test_task['status']
        result_task_id = test_task_result.get_task_id()
        result_alm_id = test_task_result.get_alm_id()
        result_status = test_task_result.get_status()
        result_timestamp = test_task_result.get_timestamp()

        self.assertEqual(result_task_id, task_id, 'Expected task id %s, got %s' % (task_id, result_task_id))
        self.assertEqual(result_alm_id, alm_id, 'Expected alm_id %s, got %s' % (alm_id, result_alm_id))
        self.assertEqual(result_status, alm_status, 'Expected %s status, got %s' % (alm_status, result_status))
        self.assertEqual(type(result_timestamp), datetime, 'Expected a datetime object')

    def test_parse_non_done_status_as_todo(self):
        self.tac.alm_connect()
        test_task = MOCK_SDE.generate_sde_task()
        self.tac.alm_add_task(test_task)
        test_task_result = self.tac.alm_get_task(test_task)
        test_task_result.status = "Non-done status"

        self.assertEqual(test_task_result.get_status(), "TODO", 'Expected status to default to TODO')

    def test_with_project_version(self):
        self.config['alm_project_version'] = '1.0'
        self.post_parse_config()  # Re-init with project version
        self.tac.alm_connect()
        test_task = MOCK_SDE.generate_sde_task()
        self.tac.alm_add_task(test_task)
        test_task_result = self.tac.alm_get_task(test_task)

        self.assertEqual(test_task_result.versions, ['1.0'])


class TestJiraAPI6Case(JiraBaseCase, unittest.TestCase):
    def test_fail_connect_server(self):
        MOCK_RESPONSE.set_response_flags({'get_projects': '500'})

        self.assert_exception(AlmException, '', 'HTTP Error 500: Server error', self.tac.alm_plugin.connect_server)

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
        self.tac.initialize()
        self.tac.alm_connect()

        self.assertEqual(self.tac.alm_plugin.custom_fields[0]['field'], "customField")
        self.assertEqual(self.tac.alm_plugin.custom_fields[0]['value'], "value")

    def assert_markdown(self, content, expected):
        converted_text = self.tac.convert_markdown_to_alm(content, None)

        self.assertEqual(converted_text, expected, 'Expected %s, got %s' % (expected, converted_text))


class MockSoapProxy():
    def __init__(self, wsdlsource, config=Config, **kw ):
        pass

    def __getattr__(self, name):
        return partial(self.get_response, name, MOCK_RESPONSE.get_response_flags())

    @staticmethod
    def get_response(*args, **keywords):
        return MOCK_RESPONSE.get_response_generator().get_proxy_response(args)


class TestJiraAPI4Case(JiraBaseCase, unittest.TestCase):
    def post_parse_config(self):
        super(TestJiraAPI4Case, self).post_parse_config()
        self.config['jira_version'] = '4'
        self.config.jira_api_ver = 4
        self.tac.alm_plugin = JIRASoapAPI(self.config)

        mock_opener = MagicMock()
        mock_opener.open = lambda x: x
        patch('sdetools.modules.sync_jira.jira_soap.http_req.get_opener', mock_opener).start()
        mock_proxy = MockSoapProxy
        patch('sdetools.modules.sync_jira.jira_soap.SOAPpy.WSDL.Proxy', mock_proxy).start()

    def test_bad_credentials(self):
        MOCK_RESPONSE.set_response_flags({'login': '401'})

        self.assert_exception(AlmException, '', 'Unable to login to JIRA. Please check ID, password',
                              self.tac.alm_plugin.connect_server)

    def test_custom_fields(self):
        self.tac.alm_connect()
        self.config['alm_custom_fields'] = {"Custom Field":"value"}
        test_task = MOCK_SDE.generate_sde_task()
        self.tac.alm_add_task(test_task)
        alm_task = self.tac.alm_get_task(test_task)
        self.config['jira_existing_issue'] = alm_task.get_alm_id()
        print alm_task.get_alm_id()
        self.tac.initialize()
        self.tac.alm_connect()

        self.assertEqual(self.tac.alm_plugin.custom_fields[0]['field'], "customField")
        self.assertEqual(self.tac.alm_plugin.custom_fields[0]['value'], "value")