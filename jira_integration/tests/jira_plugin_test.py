# NOTE: Before running ensure that the options are set properly in the
# configuration file

import sys, os, unittest
sys.path.append(os.path.split(os.path.split(os.path.split(os.path.abspath(__file__))[0])[0])[0])

from alm_integration.tests.alm_plugin_test_helper import AlmPluginTestHelper
from sdelib.conf_mgr import config
from sdelib.interactive_plugin import PlugInExperience
from jira_integration.lib.jira_plugin import JIRATask, JIRAConnector
from jira_integration.lib.jira_plugin import JIRABase, add_jira_config_options

CONF_FILE_LOCATION = 'test_settings.conf'

class TestJiraCase(AlmPluginTestHelper, unittest.TestCase):
    def setUp(self):
        add_jira_config_options(config)
        config.parse_config_file(CONF_FILE_LOCATION)
        self.tac = JIRAConnector(PlugInExperience(config), JIRABase(config))
        super(TestJiraCase, self).setUp()

if __name__ == "__main__":
    unittest.main()
