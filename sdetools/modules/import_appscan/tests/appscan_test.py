import unittest

from sdetools.sdelib.commons import UsageError
from sdetools.analysis_integration.tests.base_integration_test import BaseIntegrationTest
from sdetools.modules.import_appscan.appscan_integrator import AppScanIntegrator


class TestAppScanIntegration(BaseIntegrationTest, unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sde_cmd = "import_appscan"
        mapping_file = 'mapping.xml'
        report_file = 'appscan.xml'
        integrator = AppScanIntegrator
        super(TestAppScanIntegration, cls).setUpClass(sde_cmd, mapping_file, report_file, integrator)

    def expected_number_of_findings(self):
        return 2

    def test_appscan_standard_import_with_zip(self):
        self._test_import_with_zip()
        self.assertTrue(self.integrator.TOOL_NAME == 'appscan', 'Detected AppScan Standard report')

    def test_appscan_enterprise_import_with_zip(self):
        self.report_file = 'appscan_enterprise.xml'
        self._test_import_with_zip()
        self.assertTrue(self.integrator.TOOL_NAME == 'appscan_enterprise', 'Detected AppScan Enterprise report')

    def test_appscan_enterprise_import_findings_assert_passed_tasks(self):
        self.report_file = 'appscan_enterprise.xml'
        self.init_integrator()
        self.test_import_findings_assert_passed_tasks()
        self.assertTrue(self.integrator.TOOL_NAME == 'appscan_enterprise', 'Detected AppScan Enterprise report')

    def test_invalid_edition(self):
        self.config['edition'] = 'unknown'
        try:
            self.init_data()
            self.assertTrue(False, 'Unsupported AppScan edition: %s' % self.config['edition'])
        except UsageError:
            pass
