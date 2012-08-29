#NOTE: Before running ensure that the options are set
#properly in the configuration file

import sys, os, unittest
sys.path.append(os.path.split(os.path.split(os.path.split(os.path.abspath(__file__))[0])[0])[0])

from alm_integration.tests.alm_plugin_test_helper import AlmPluginTestHelper
from sdelib.conf_mgr import config
from sdelib.interactive_plugin import PlugInExperience
from rally_integration.lib.rally_plugin import RallyTask, RallyConnector
from rally_integration.lib.rally_plugin import add_rally_config_options
from rally_integration.lib.rally_plugin import RallyAPIBase


CONF_FILE_LOCATION = 'test_settings.conf'

class TestRallyCase(AlmPluginTestHelper, unittest.TestCase):
     def setUp(self):
        add_rally_config_options(config)
        config.parse_config_file(CONF_FILE_LOCATION)
        self.tac = RallyConnector(PlugInExperience(config), RallyAPIBase(config))
        super(TestRallyCase, self).setUp()
        
if __name__ == "__main__":
    unittest.main()

