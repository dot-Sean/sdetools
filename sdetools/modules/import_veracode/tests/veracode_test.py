import unittest

from sdetools.analysis_integration.tests.base_integration_test import BaseIntegrationTest
from sdetools.modules.import_veracode.veracode_integrator import VeracodeIntegrator


class TestVeracodeIntegration(BaseIntegrationTest, unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sde_cmd = "import_veracode"
        mapping_file = 'mapping.xml'
        report_file = 'report.xml'
        integrator = VeracodeIntegrator
        super(TestVeracodeIntegration, cls).setUpClass(sde_cmd, mapping_file, report_file, integrator)

    def expected_number_of_findings(self):
        return 2

