# NOTE: Before running ensure that the options are set properly in the
#       configuration file
import unittest

from sdetools.alm_integration.tests.alm_plugin_live_test_base import AlmPluginLiveTestBase
from sdetools.modules.sync_pt.pt_plugin import PivotalTrackerConnector, PivotalTrackerAPI


class TestPivotalTrackerLiveCase(AlmPluginLiveTestBase, unittest.TestCase):
    @classmethod
    def setUpClass(self):
        super(TestPivotalTrackerLiveCase, self).setUpClass(PivotalTrackerConnector, PivotalTrackerAPI)