import unittest
import os

from sdetools.analysis_integration.tests.base_integration_test import BaseIntegrationTest
from sdetools.modules.import_fortify.fortify_integrator import FortifyIntegrator
from sdetools.analysis_integration.base_integrator import IntegrationError

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

    def test_import_failed_fpr_missing_files(self):
        tests = [{'fpr': 'fail-no-audit-fvdl.fpr', 'file': 'audit.fvdl'},
                 {'fpr': 'fail-no-audit-xml.fpr', 'file': 'audit.xml'}]

        for test in tests:
            self.integrator.config['report_file'] = os.path.join(self.test_file_dir, test['fpr'])
            self.assert_exception(IntegrationError, "FATAL ERROR: Error processing %s: FATAL ERROR: File %s not found" %
                                  (self.integrator.config['report_file'], test['file']), self.init_data)

    def test_report_import(self):
        self.integrator.config['report_file'] = os.path.join(self.test_file_dir, 'webgoat.xml')
        self.init_data()
        findings = self.integrator.generate_findings()
        self.assertTrue(self.integrator.report_id, 'Expected a report_id value')
        self.assertTrue(len(findings), 'Expected to process some findings')

    def test_import_auditxml_missing_project_name(self):
        self.integrator.config['report_file'] = os.path.join(self.test_file_dir, 'audit-xml-missing-project-name.fpr')
        self.init_data()

        findings = self.integrator.generate_findings()
        self.assertTrue(self.integrator.report_id, 'Expected a report_id value')
        self.assertTrue(len(findings), 'Expected to process some findings')