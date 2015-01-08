# NOTE: Before running ensure that the options are set properly in the
#       configuration file
import unittest

from sdetools.alm_integration.tests.alm_plugin_live_test_base import AlmPluginLiveTestBase
from sdetools.modules.sync_hp_alm.hp_alm_plugin import HPAlmConnector, HPAlmAPIBase


class TestHPAlmLiveCase(AlmPluginLiveTestBase, unittest.TestCase):
    @classmethod
    def setUpClass(self):
        super(TestHPAlmLiveCase, self).setUpClass(HPAlmConnector, HPAlmAPIBase)

    def test_synchronize_sde_as_master(self):
        pass

    def test_custom_titles(self):
        pass