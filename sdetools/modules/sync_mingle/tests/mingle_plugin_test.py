import sys, os, unittest
from urllib2 import HTTPError
from json import JSONEncoder
from mock import patch
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))))

from sdetools.alm_integration.tests.alm_plugin_test_base import AlmPluginTestBase
from sdetools.modules.sync_mingle.mingle_plugin import MingleConnector, MingleAPIBase, APIError
from sdetools.sdelib.conf_mgr import Config
from sdetools.sdelib.restclient import URLRequest, APIFormatError
from mingle_response_generator import MingleResponseGenerator

CONF_FILE_LOCATION = 'test_settings.conf'
MOCK_FLAG = None
MINGLE_RESPONSE_GENERATOR = None
def mock_call_api(self, target, method=URLRequest.GET, args=None, call_headers={}):
    try:
        return MINGLE_RESPONSE_GENERATOR.get_response(target, MOCK_FLAG, args, method)
    except HTTPError, err:
        # Re-raise with more info
        err.url = '%s/%s' % (err.url, target)
        err.headers = call_headers
        raise APIError(err)

class TestMingleCase():
    @classmethod
    def setUpClass(self):
        PATH_TO_MINGLE_CONNECTOR = 'sdetools.modules.sync_mingle.github_mingle'
        super(TestMingleCase, self).initTest(PATH_TO_MINGLE_CONNECTOR)

        conf_path = os.path.abspath('%s\%s' % (os.path.dirname(os.path.realpath(__file__)), CONF_FILE_LOCATION))
        self.tac = MingleConnector(self.config, MingleAPIBase(self.config))
        Config.parse_config_file(self.config, conf_path)
        self.tac.initialize()

        global MINGLE_RESPONSE_GENERATOR
        MINGLE_RESPONSE_GENERATOR = MingleResponseGenerator(self.config['alm_server'],
                                                            self.config['alm_project'],
                                                            self.config['alm_project_version'],
                                                            self.config['alm_user'])
        patch('%s.RESTBase.call_api' % PATH_TO_MINGLE_CONNECTOR, mock_call_api).start()                                                        

    def setUp(self):
        super(TestMingleCase, self).setUp()

    def tearDown(self):
        super(TestMingleCase, self).tearDown()
        MINGLE_RESPONSE_GENERATOR.clear_alm_tasks()