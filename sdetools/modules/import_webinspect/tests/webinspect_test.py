import unittest
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))))

from sdetools.analysis_integration.tests.base_integration_test import BaseIntegrationTest
from sdetools.modules.import_webinspect import webinspect_integrator

TESTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'files')


class TestWebInspectIntegration(BaseIntegrationTest, unittest.TestCase):
    SDE_CMD = "import_webinspect"

    def setUp(self):
        super(TestWebInspectIntegration, self).setUp()
        self.integrator = webinspect_integrator.WebInspectIntegrator(self.config)
        self.integrator.config['mapping_file'] = os.path.join(TESTS_DIR, 'mapping.xml')
        self.integrator.config['report_file'] = os.path.join(TESTS_DIR, 'results.fpr')

    def expected_number_of_findings(self):
        return 4

    def test_import_findings(self):
        super(TestWebInspectIntegration, self).test_import_findings()

if __name__ == "__main__":
    unittest.main()