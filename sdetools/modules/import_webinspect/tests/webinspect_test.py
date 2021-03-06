import unittest

from sdetools.analysis_integration.tests.base_integration_test import BaseIntegrationTest
from sdetools.modules.import_webinspect.webinspect_integrator import WebInspectIntegrator


class TestWebInspectIntegration(BaseIntegrationTest, unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sde_cmd = "import_webinspect"
        mapping_file = 'mapping.xml'
        report_file = 'webinspect.xml'
        integrator = WebInspectIntegrator
        super(TestWebInspectIntegration, cls).setUpClass(sde_cmd, mapping_file, report_file, integrator)

    def expected_number_of_findings(self):
        return 2

    def test_import_with_zip(self):
        self._test_import_with_zip()

if __name__ == "__main__":
    unittest.main()
