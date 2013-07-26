import os
import re
from sdetools.extlib.defusedxml import minidom

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
        config.add_custom_option("report_xml", "AppScan Report XML", "x", None)
        super(AppScanIntegrator, self).__init__(config, DEFAULT_MAPPING_FILE)
        self.raw_findings = []

    def parse(self):
        try:
            fileName, file_extension = os.path.splitext(self.config['report_xml'])
        except KeyError, ke:
            raise AppScanIntegrationError("Missing configuration option 'report_xml'")
              
        if file_extension == '.xml':
            self.importer = AppScanXMLImporter()
        else:
            raise AppScanIntegrationError("Unsupported file type (%s)" % file_extension)

        self.importer.parse(self.config['report_xml'])
        self.raw_findings = self.importer.raw_findings
        self.report_id = self.importer.report_id

        if self.report_id is None or self.report_id == "":
            raise AppScanIntegrationError("Report ID not found in report file (%s)" % self.config['report_xml'])

    def _make_finding(self, item):
        return {'weakness_id': item['id'], 'description': item['description'], 'count':item['count']}

    def generate_findings(self):
        return [self._make_finding(item) for item in self.raw_findings]
