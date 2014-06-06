# NOTE: Before running ensure that the options are set properly in the
#       configuration file
import unittest

from sdetools.alm_integration.tests.alm_plugin_live_test_base import AlmPluginLiveTestBase
from sdetools.modules.sync_jira.jira_plugin import JIRAConnector
from sdetools.modules.sync_jira.jira_soap import JIRASoapAPI
from sdetools.modules.sync_jira.jira_rest import JIRARestAPI


class TestJIRASoapLiveCase(AlmPluginLiveTestBase, unittest.TestCase):
    @classmethod
    def setUpClass(self):
        super(TestJIRASoapLiveCase, self).setUpClass(JIRAConnector, JIRARestAPI)

    def setUp(self):
        super(TestJIRASoapLiveCase, self).setUp()
        self.connector.config.jira_api_ver = 4
        self.connector.alm_plugin = JIRASoapAPI(self.config)