# NOTE: Before running ensure that the options are set properly in the
#       configuration file
import unittest

from sdetools.alm_integration.tests.alm_plugin_live_test_base import AlmPluginLiveTestBase
from sdetools.modules.sync_github.github_plugin import GitHubConnector, GitHubAPI


class TestGitHubLiveCase(AlmPluginLiveTestBase, unittest.TestCase):
    @classmethod
    def setUpClass(self):
        super(TestGitHubLiveCase, self).setUpClass(GitHubConnector, GitHubAPI)