# NOTE: Before running ensure that the options are set properly in the
#       configuration file
import unittest

from github_response_generator import GitHubResponseGenerator
from sdetools.alm_integration.tests.alm_plugin_test_base import AlmPluginTestBase
from sdetools.modules.sync_github.github_plugin import GitHubConnector, GitHubAPI, AlmException


class TestGitHubCase(AlmPluginTestBase, unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        alm_classes = [GitHubConnector, GitHubAPI, GitHubResponseGenerator]
        super(TestGitHubCase, cls).setUpClass(alm_classes=alm_classes)

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

    def test_invalid_api_token(self):
        self.mock_alm_response.set_response_flags({'get_user': '401'})
        self.connector.config['alm_api_token'] = 'testApiToken'

        exception_msg = 'Unable to connect to GitHub service (Check server URL, api token). Reason: '\
                        'HTTP Error 401. Explanation returned: FATAL ERROR: Requires authentication'

        self.assert_exception(AlmException, '', exception_msg, self.connector.alm_connect_server)

    def test_invalid_user_pass(self):
        self.mock_alm_response.set_response_flags({'get_user': '401'})
        self.connector.config['alm_api_token'] = ''
        exception_msg = 'Unable to connect to GitHub service (Check server URL, user, pass). Reason: '\
                        'HTTP Error 401. Explanation returned: FATAL ERROR: Requires authentication'

        self.assert_exception(AlmException, '', exception_msg, self.connector.alm_connect_server)

    def test_connecting_to_invalid_repo(self):
        self.mock_alm_response.set_response_flags({'get_repo': '404'})
        exception_msg = 'Unable to find GitHub repo. Reason: HTTP Error 404. Explanation returned: FATAL ERROR: Not found'

        self.assert_exception(AlmException, '', exception_msg, self.connector.synchronize)

    def test_nonexistant_milestone(self):
        self.mock_alm_response.set_response_flags({'get_milestones': 'nomilestone'})
        self.connector.config['alm_project_version'] = 'non-existant milestone'
        exception_msg = 'Unable to find milestone non-existant milestone from GitHub'

        self.assert_exception(AlmException, '', exception_msg, self.connector.synchronize)

    def test_invalid_field(self):
        self.mock_alm_response.set_response_flags({'post_issue': '422'})
        self.connector.alm_connect()
        test_task = self.mock_sde_response.generate_sde_task()
        exception_msg = 'Unable to add task %s to GitHub. Reason: HTTP Error 422. Explanation returned: FATAL ERROR: Validation Failed. ' \
                        'Additional Info - The field "title" is required for the resource "Issue"' % test_task['id']

        self.assert_exception(AlmException, '', exception_msg, self.connector.alm_add_task, test_task)
