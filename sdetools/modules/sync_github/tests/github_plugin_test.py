# NOTE: Before running ensure that the options are set properly in the
#       configuration file
import os
import unittest
from datetime import datetime
from github_response_generator import GitHubResponseGenerator

import sdetools.alm_integration.tests.alm_mock_response
import sdetools.alm_integration.tests.alm_mock_sde_plugin
from sdetools.alm_integration.tests.alm_plugin_test_base import AlmPluginTestBase
from sdetools.modules.sync_github.github_plugin import GitHubConnector, GitHubAPI, AlmException

CONF_FILE_LOCATION = 'test_settings.conf'
MOCK_RESPONSE = sdetools.alm_integration.tests.alm_mock_response
MOCK_SDE = sdetools.alm_integration.tests.alm_mock_sde_plugin


class TestGitHubCase(AlmPluginTestBase, unittest.TestCase):
    @classmethod
    def setUpClass(self):
        path_to_github_connector = 'sdetools.modules.sync_github.github_plugin'
        current_dir = os.path.dirname(os.path.realpath(__file__))
        conf_path = os.path.join(current_dir, CONF_FILE_LOCATION)
        super(TestGitHubCase, self).setUpClass(path_to_github_connector, conf_path)

    def init_alm_connector(self):
        connector = GitHubConnector(self.config, GitHubAPI(self.config))
        super(TestGitHubCase, self).init_alm_connector(connector)

    def post_parse_config(self):
        response_generator = GitHubResponseGenerator(self.config['alm_server'],
                                                     self.config['github_repo_owner'],
                                                     self.config['alm_project'],
                                                     self.config['alm_project_version'],
                                                     self.config['alm_user'])

        MOCK_RESPONSE.patch_call_rest_api(response_generator, self.path_to_alm_connector)

    def test_parsing_alm_task(self):
        result = super(TestGitHubCase, self).test_parsing_alm_task()
        test_task = result[0]
        test_task_result = result[1]

        alm_id = test_task['id'].split('T')[1]
        alm_status = test_task['status']
        result_alm_id = test_task_result.get_alm_id()
        result_status = test_task_result.get_status()
        result_timestamp = test_task_result.get_timestamp()

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

    def test_connecting_to_public_repo(self):
        MOCK_RESPONSE.set_response_flags({'get_repo': 'private-false'})
        self.assert_exception(AlmException, '',
                              'Syncing with a public repository is currently not supported',
                              self.tac.alm_connect_project)

    def test_connecting_to_invalid_repo(self):
         MOCK_RESPONSE.set_response_flags({'get_repo': '404'})
         self.assert_exception(AlmException, '',
                               'Unable to find GitHub repo. Reason: FATAL ERROR: HTTP Error 404: Not found',
                               self.tac.alm_connect_project)
