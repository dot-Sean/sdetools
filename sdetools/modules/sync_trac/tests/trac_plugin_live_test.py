# NOTE: Before running ensure that the options are set properly in the
#       configuration file
import unittest

from sdetools.alm_integration.tests.alm_plugin_live_test_base import AlmPluginLiveTestBase
from sdetools.modules.sync_trac.trac_plugin import TracConnector, TracXMLRPCAPI


class TestTracLiveCase(AlmPluginLiveTestBase, unittest.TestCase):
    @classmethod
    def setUpClass(self):
        super(TestTracLiveCase, self).setUpClass(TracConnector, TracXMLRPCAPI)
