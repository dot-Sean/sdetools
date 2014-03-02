# NOTE: Before running ensure that the options are set properly in the
#       configuration file
import unittest

from sdetools.alm_integration.tests.alm_plugin_live_test_base import AlmPluginLiveTestBase
from sdetools.modules.sync_rational.rational_plugin import RationalConnector, RationalAPI


class TestRationalLiveCase(AlmPluginLiveTestBase, unittest.TestCase):
    @classmethod
    def setUpClass(self):
        super(TestRationalLiveCase, self).setUpClass(RationalConnector, RationalAPI)

    def test_synchronize_sde_as_master(self):
        pass
