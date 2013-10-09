#NOTE: Before running ensure that the options are set
#properly in the configuration file

import unittest
import os


from sdetools.analysis_integration.tests.base_integration_test import BaseIntegrationTest
from sdetools.modules.import_veracode.veracode_integrator import VeracodeIntegrator

TESTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'files')

CONF_FILE_LOCATION = 'test_settings.conf'

class TestVeracode(BaseIntegrationTest, unittest.TestCase):
    def init_integrator(self):
        self.integrator = VeracodeIntegrator(self.config)
        self.integrator.config['mapping_file'] = os.path.join(TESTS_DIR, 'mapping.xml')
        self.integrator.config['report_file'] = os.path.join(TESTS_DIR, 'report.xml')

    def expected_number_of_findings(self):
        return 2

if __name__ == "__main__":
    unittest.main()

