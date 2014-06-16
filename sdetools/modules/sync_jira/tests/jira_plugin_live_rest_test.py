# NOTE: Before running ensure that the options are set properly in the
#       configuration file
import unittest

from sdetools.alm_integration.tests.alm_plugin_live_test_base import AlmPluginLiveTestBase
from sdetools.modules.sync_jira.jira_plugin import JIRAConnector
from sdetools.modules.sync_jira.jira_rest import JIRARestAPI


class TestJIRARestLiveCase(AlmPluginLiveTestBase, unittest.TestCase):
    @classmethod
    def setUpClass(self):
        super(TestJIRARestLiveCase, self).setUpClass(JIRAConnector, JIRARestAPI)

    def setUp(self):
        super(TestJIRARestLiveCase, self).setUp()
        self.connector.config.jira_api_ver = 5

    def test_alm_supports_delete(self):
        self.assertTrue(self.connector.alm_supports_delete())