import unittest
import os

from sdetools.analysis_integration.tests.base_integration_test import BaseIntegrationTest
from sdetools.modules.import_appscan import appscan_integrator

TESTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'files')

class TestAppScanIntegration(BaseIntegrationTest, unittest.TestCase):
    SDE_CMD = "import_appscan"

    def init_integrator(self):
        self.integrator = appscan_integrator.AppScanIntegrator(self.config)
        self.integrator.config['mapping_file'] = os.path.join(TESTS_DIR, 'mapping.xml')
        self.integrator.config['report_file'] = os.path.join(TESTS_DIR, 'results.zip')

    def expected_number_of_findings(self):
        return 2
