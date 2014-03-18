# NOTE: Before running ensure that the options are set properly in the
#       configuration file
import unittest

from sdetools.alm_integration.tests.alm_plugin_live_test_base import AlmPluginLiveTestBase
from sdetools.modules.sync_mingle.mingle_plugin import MingleConnector, MingleAPIBase


class TestMingleLiveCase(AlmPluginLiveTestBase, unittest.TestCase):
    @classmethod
    def setUpClass(self):
        super(TestMingleLiveCase, self).setUpClass(MingleConnector, MingleAPIBase)