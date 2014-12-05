import unittest

from sdetools.sdelib.commons import UsageError
from sdetools.analysis_integration.tests.base_integration_test import BaseIntegrationTest
from sdetools.modules.import_appscan.appscan_integrator import AppScanIntegrator
from sdetools.modules.import_appscan.appscan_zip_importer import AppScanZIPImporter


class TestAppScanIntegration(BaseIntegrationTest, unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sde_cmd = "import_appscan"
        mapping_file = 'mapping.xml'
        report_file = 'results.zip'
        integrator = AppScanIntegrator
        super(TestAppScanIntegration, cls).setUpClass(sde_cmd, mapping_file, report_file, integrator)

    def expected_number_of_findings(self):
        return 2

    def test_invalid_edition(self):
        self.config['edition'] = 'unknown'
        try:
            self.init_data()
            self.assertTrue(False, 'Unsupported AppScan edition: %s' % self.config['edition'])
        except UsageError:
            self.assertTrue(True)