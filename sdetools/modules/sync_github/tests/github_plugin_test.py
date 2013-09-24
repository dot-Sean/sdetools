# NOTE: Before running ensure that the options are set properly in the
#       configuration file

import sys, os, unittest
from urllib2 import HTTPError
from json import JSONEncoder
from mock import patch
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))))

from sdetools.alm_integration.tests.alm_plugin_test_base import AlmPluginTestBase
from sdetools.modules.sync_github.github_plugin import GitHubConnector, GitHubAPI, APIError
from sdetools.sdelib.conf_mgr import Config
from sdetools.sdelib.restclient import URLRequest, APIFormatError
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
    def setUpClass(self):
        PATH_TO_GITHUB_CONNECTOR = 'sdetools.modules.sync_github.github_plugin'
        super(TestGitHubCase, self).initTest(PATH_TO_GITHUB_CONNECTOR)

        conf_path = os.path.abspath('%s\%s' % (os.path.dirname(os.path.realpath(__file__)), CONF_FILE_LOCATION))
        self.tac = GitHubConnector(self.config, GitHubAPI(self.config))
        Config.parse_config_file(self.config, conf_path)
        self.tac.initialize()

        global GITHUB_RESPONSE_GENERATOR
        GITHUB_RESPONSE_GENERATOR = GitHubResponseGenerator(self.config['alm_server'],
                                                        self.config['github_repo_owner'],
                                                        self.config['alm_project'],
                                                        self.config['alm_project_version'],
                                                        self.config['alm_user'])
        patch('sdetools.modules.sync_github.github_plugin.RESTBase.call_api', mock_call_api).start()                                                        

    def setUp(self):
        super(TestGitHubCase, self).setUp()

    def tearDown(self):
        super(TestGitHubCase, self).tearDown()
        GITHUB_RESPONSE_GENERATOR.clear_github_tasks()
