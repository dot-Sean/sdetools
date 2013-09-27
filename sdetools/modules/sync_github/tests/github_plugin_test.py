# NOTE: Before running ensure that the options are set properly in the
#       configuration file
import sys
import os
import unittest

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))))
from sdetools.alm_integration.tests.alm_plugin_test_base import AlmPluginTestBase
import sdetools.alm_integration.tests.alm_mock_response
from sdetools.modules.sync_github.github_plugin import GitHubConnector, GitHubAPI, AlmException
from github_response_generator import GitHubResponseGenerator

CONF_FILE_LOCATION = 'test_settings.conf'
MOCK_REST_API = sdetools.alm_integration.tests.alm_mock_response


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

    def init_response_generator(self):
        response_generator = GitHubResponseGenerator(self.config['alm_server'],
                                                     self.config['github_repo_owner'],
                                                     self.config['alm_project'],
                                                     self.config['alm_project_version'],
                                                     self.config['alm_user'])

        path_to_rest_plugin = 'sdetools.modules.sync_github.github_plugin'
        MOCK_REST_API.patch_call_rest_api(response_generator, path_to_rest_plugin)

    def setUp(self):
        super(TestGitHubCase, self).setUp()

    def tearDown(self):
        super(TestGitHubCase, self).tearDown()

    def test_connecting_to_public_repo(self):
        MOCK_REST_API.set_mock_flag({'get_repo': 'private-false'})
        self.assert_exception(AlmException, '',
                              'Syncing with a public repository is currently not supported',
                              self.tac.alm_connect_project)

    def test_connecting_to_invalid_repo(self):
         MOCK_REST_API.set_mock_flag({'get_repo': '404'})
         self.assert_exception(AlmException, '',
                               'Unable to find GitHub repo. Reason: FATAL ERROR: HTTP Error 404: Not found',
                               self.tac.alm_connect_project)