# NOTE: Before running ensure that the options are set properly in the
#       configuration file

import sys, os, unittest
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))))

from sdetools.alm_integration.tests.alm_plugin_test_base import AlmPluginTestBase

from sdetools.sdelib.conf_mgr import Config
from sdetools.sdelib.mod_mgr import ReturnChannel
from sdetools.sdelib.interactive_plugin import PlugInExperience
from sdetools.modules.sync_jira.jira_plugin import JIRAConnector

from mock import patch
from sdetools.sdelib.restclient import URLRequest, APIFormatError
from sdetools.alm_integration.alm_plugin_base import AlmException
from sdetools.modules.sync_jira.jira_rest import APIError
from jira_response_generator import JiraResponseGenerator
from urllib2 import HTTPError
from json import JSONEncoder

MOCK_FLAG = None
JIRA_RESPONSE_GENERATOR = None

def mock_call_api(self, target, method=URLRequest.GET, args=None, call_headers={}):
    try:
        return JIRA_RESPONSE_GENERATOR.get_response(target, MOCK_FLAG, args, method)
    except HTTPError, err:
        # Re-raise with more info
        err.url = '%s/%s' % (err.url, target)
        err.headers = call_headers
        raise APIError(err)

patch('sdetools.modules.sync_jira.jira_rest.RESTBase.call_api', mock_call_api).start()
from sdetools.modules.sync_jira.jira_rest import JIRARestAPI

CONF_FILE_LOCATION = 'test_settings.conf'
def stdout_callback(obj):
    print obj
    
class TestJiraCase(AlmPluginTestBase, unittest.TestCase):
    def setUp(self):
        """ Jira Tests """ 
        conf_path = os.path.abspath('%s\%s' % (os.path.dirname(os.path.realpath(__file__)), CONF_FILE_LOCATION))
        ret_chn = ReturnChannel(stdout_callback, {})
        config = Config('', '', ret_chn, 'import')
        self.tac = JIRAConnector(config, JIRARestAPI(config))
        Config.parse_config_file(config, conf_path)
        global JIRA_RESPONSE_GENERATOR
        JIRA_RESPONSE_GENERATOR = JiraResponseGenerator(config['alm_server'],
                                                        config['alm_project'],
                                                        config['alm_project_version'],
                                                        config['alm_user'])
        super(TestJiraCase, self).setUp()
    
    def test_sde(self):
        """ Test SDE Mock """
        # Assert mock connect doesn't throw error
        self.tac.sde_connect()
        # Test connection status
        self.assertTrue(self.tac.is_sde_connected())
        # Test SDE get all tasks
        tasklist = self.tac.sde_get_tasks()
        self.assertTrue(tasklist)
        for task in tasklist:
            self.assertTrue(task.has_key('status'))
            self.assertTrue(task.has_key('timestamp'))
            self.assertTrue(task.has_key('phase'))
            self.assertTrue(task.has_key('id'))
            self.assertTrue(task.has_key('priority'))
            self.assertTrue(task.has_key('note_count'))
        # Test SDE get single task
        task = self.tac.sde_get_task('1000-T1')
        self.assertTrue(task)
        # Assert update status doesn't throw error
        self.tac.sde_update_task_status('task', 'status')
        # Test SDE get content
        self.assertEqual(self.tac.sde_get_task_content('task'), 'Task content')

    def test_connect(self):
        """[JIRA] Test mocked Jira connection """
        # Assert Server Success
        self.tac.alm_plugin.connect_server
        # Assert Project Success
        self.tac.alm_plugin.connect_project
        # Assert Error
        global MOCK_FLAG
        MOCK_FLAG = 'fail'
        self.assertRaises(APIError, self.tac.alm_plugin.call_api, 'project')
        MOCK_FLAG = None

    def test_parse_result(self):
        """[JIRA] Test response parser """
        # Assert bad json error checking
        result = "crappy json"
        self.assertRaises(APIFormatError, self.tac.alm_plugin.parse_response, result)
        # Assert successful json parsing
        result = self.tac.alm_plugin.call_api('project')
        encoded_result = JSONEncoder().encode(result)
        json = self.tac.alm_plugin.parse_response(encoded_result)
        self.assertTrue(json[0].get('self'))
        self.assertTrue(json[0].get('id'))
        self.assertTrue(json[0].get('key'))
        self.assertTrue(json[0].get('name'))
        self.assertTrue(json[0].get('avatarUrls'))
        self.assertTrue(json[0].get('avatarUrls').get('24x24'))
        self.assertFalse(json[0].get('non-existant-key'))

    if __name__ == "__main__":
        unittest.main()