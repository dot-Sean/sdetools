# NOTE: Before running ensure that the options are set properly in the
#       configuration file
import sys
import os
import unittest
from urllib2 import HTTPError
from mock import patch

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))))
from sdetools.alm_integration.tests.alm_plugin_test_base import AlmPluginTestBase
from sdetools.modules.sync_github.github_plugin import GitHubConnector, GitHubAPI, APIError
from sdetools.sdelib.conf_mgr import Config
from sdetools.sdelib.restclient import URLRequest
from github_response_generator import GitHubResponseGenerator

CONF_FILE_LOCATION = 'test_settings.conf'
MOCK_FLAG = None
GITHUB_RESPONSE_GENERATOR = None


def mock_call_api(self, target, method=URLRequest.GET, args=None, call_headers={}):
    try:
        return GITHUB_RESPONSE_GENERATOR.get_response(target, MOCK_FLAG, args, method)
    except HTTPError, err:
        # Re-raise with more info
        err.url = '%s/%s' % (err.url, target)
        err.headers = call_headers
        raise APIError(err)


class TestGitHubCase(AlmPluginTestBase, unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path_to_github_connector = 'sdetools.modules.sync_github.github_plugin'
        super(TestGitHubCase, cls).initTest(path_to_github_connector)

        conf_path = os.path.abspath('%s\%s' % (os.path.dirname(os.path.realpath(__file__)), CONF_FILE_LOCATION))
        cls.tac = GitHubConnector(cls.config, GitHubAPI(cls.config))
        Config.parse_config_file(cls.config, conf_path)
        cls.tac.initialize()

        global GITHUB_RESPONSE_GENERATOR
        GITHUB_RESPONSE_GENERATOR = GitHubResponseGenerator(cls.config['alm_server'],
                                                            cls.config['github_repo_owner'],
                                                            cls.config['alm_project'],
                                                            cls.config['alm_project_version'],
                                                            cls.config['alm_user'])
        patch('sdetools.modules.sync_github.github_plugin.RESTBase.call_api', mock_call_api).start()                                                        

    def setUp(self):
        super(TestGitHubCase, self).setUp()

    def tearDown(self):
        super(TestGitHubCase, self).tearDown()
        GITHUB_RESPONSE_GENERATOR.clear_alm_tasks()
