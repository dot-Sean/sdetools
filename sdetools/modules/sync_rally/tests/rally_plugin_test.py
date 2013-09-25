#NOTE: Before running ensure that the options are set
#properly in the configuration file

import sys, os, unittest
sys.path.append(os.path.split(os.path.split(os.path.split(os.path.abspath(__file__))[0])[0])[0])

from sdetools.alm_integration.tests.alm_plugin_test_base import AlmPluginTestBase
from sdetools.sdelib.conf_mgr import Config
from sdetools.sdelib.interactive_plugin import PlugInExperience
from sdetools.modules.sync_rally.rally_plugin import RallyConnector, RallyAPIBase

CONF_FILE_LOCATION = 'test_settings.conf'

class TestRallyCase(unittest.TestCase):
     def setUp(self):
        pass
        
if __name__ == "__main__":
    unittest.main()

