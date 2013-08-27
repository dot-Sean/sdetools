import os

from sdetools.sdelib import commons
from sdetools.analysis_integration.base_integrator import BaseIntegrator, IntegrationError
from sdetools.modules.import_appscan.appscan_xml_importer import AppScanXMLContent, AppScanXMLImporter

__all__ = ['AppScanIntegrator']

DEFAULT_MAPPING_FILE = os.path.join(commons.media_path, 'appscan', 'sde_appscan_map.xml')

class AppScanIntegrationError(IntegrationError):
    pass

class AppScanIntegrator(BaseIntegrator):
    TOOL_NAME = "fortify"

    def __init__(self, config):
        config.add_custom_option("report_file", "AppScan Report XML", "x", None)
        config.add_custom_option("report_type", "AppScan Report Type: xml|auto", default="auto")
        super(AppScanIntegrator, self).__init__(config, DEFAULT_MAPPING_FILE)
        self.raw_findings = []

    def parse(self):

        if not self.config['report_file']:
            raise UsageError("Missing configuration option 'report_file'")

        if self.config['report_type'] == 'auto': 
            if not isinstance(self.config['report_file'], basestring):
                raise UsageError("On auto-detect mode, the file name needs to be specified.")
            fileName, file_extension = os.path.splitext(self.config['report_file'])
            self.config['report_type'] = file_extension[1:]

        if self.config['report_type'] == 'xml':
            self.importer = AppScanXMLImporter()
        else:
            raise UsageError("Unsupported file type (%s)" % self.config['report_type'])

        self.importer.parse(self.config['report_file'])
        self.raw_findings = self.importer.raw_findings
        self.report_id = self.importer.report_id

        if self.importer.report_id:
            self.report_id = self.importer.report_id
        else:
            logger.info("Report ID not found in report")

    def _make_finding(self, item):
        return {'weakness_id': item['id'], 'description': item['description'], 'count':item['count']}

    def generate_findings(self):
        return [self._make_finding(item) for item in self.raw_findings]
