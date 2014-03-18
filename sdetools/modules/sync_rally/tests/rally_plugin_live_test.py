# NOTE: Before running ensure that the options are set properly in the
#       configuration file
import unittest

from sdetools.alm_integration.tests.alm_plugin_live_test_base import AlmPluginLiveTestBase
from sdetools.modules.sync_rally.rally_plugin import RallyConnector, RallyAPIBase


class TestRallyLiveCase(AlmPluginLiveTestBase, unittest.TestCase):
    @classmethod
    def setUpClass(self):
        super(TestRallyLiveCase, self).setUpClass(RallyConnector, RallyAPIBase)