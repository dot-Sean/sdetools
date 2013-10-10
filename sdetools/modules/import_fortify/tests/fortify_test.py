import unittest

from sdetools.analysis_integration.tests.base_integration_test import BaseIntegrationTest
from sdetools.modules.import_fortify.fortify_integrator import FortifyIntegrator


class TestFortifyIntegration(BaseIntegrationTest, unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sde_cmd = "import_fortify"
        mapping_file = 'mapping.xml'
        report_file = 'results.fpr'
        integrator = FortifyIntegrator
        super(TestFortifyIntegration, cls).setUpClass(sde_cmd, mapping_file, report_file, integrator)

    def expected_number_of_findings(self):
        return 2

if __name__ == "__main__":
    unittest.main()