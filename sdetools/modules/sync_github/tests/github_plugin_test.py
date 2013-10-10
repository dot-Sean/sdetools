# NOTE: Before running ensure that the options are set properly in the
#       configuration file
import unittest

from github_response_generator import GitHubResponseGenerator
from sdetools.alm_integration.tests.alm_plugin_test_base import AlmPluginTestBase
from sdetools.modules.sync_github.github_plugin import GitHubConnector, GitHubAPI, AlmException
PATH_TO_ALM_REST_API = 'sdetools.modules.sync_github.github_plugin'


class TestGitHubCase(AlmPluginTestBase, unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        alm_classes = [GitHubConnector, GitHubAPI, GitHubResponseGenerator]
        super(TestGitHubCase, cls).setUpClass(PATH_TO_ALM_REST_API, alm_classes=alm_classes)

    def test_parsing_alm_task(self):
        result = super(TestGitHubCase, self).test_parsing_alm_task()
        test_task = result[0]
        test_task_result = result[1]
        alm_id = test_task['id'].split('T')[1]
        result_alm_id = test_task_result.get_alm_id()

        self.assertEqual(result_alm_id, alm_id, 'Expected alm_id %s, got %s' % (alm_id, result_alm_id))

    def test_parse_non_done_status_as_todo(self):
        self.connector.alm_connect()
        test_task = self.mock_sde_response.generate_sde_task()
        self.connector.alm_add_task(test_task)
        test_task_result = self.connector.alm_get_task(test_task)
        test_task_result.status = "Non-done status"

        self.assertEqual(test_task_result.get_status(), "TODO", 'Expected status to default to TODO')

    def test_connecting_to_invalid_repo(self):
         self.mock_alm_response.set_response_flags({'get_repo': '404'})
         exception_msg = 'Unable to find GitHub repo. Reason: FATAL ERROR: HTTP Error 404: Not found'

         self.assert_exception(AlmException, '', exception_msg, self.connector.alm_connect_project)
