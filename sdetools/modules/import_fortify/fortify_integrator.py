import os

from sdetools.sdelib.commons import media_path, UsageError
from sdetools.analysis_integration.base_integrator import BaseIntegrator

from sdetools.modules.import_fortify.fortify_integration_error import FortifyIntegrationError
from sdetools.modules.import_fortify.fortify_report_importer import FortifyReportImporter
from sdetools.modules.import_fortify.fortify_fpr_importer import FortifyFPRImporter
from sdetools.modules.import_fortify.fortify_fvdl_importer import FortifyFVDLImporter

__all__ = ['FortifyIntegrator']

DEFAULT_MAPPING_FILE = os.path.join(media_path, 'fortify', 'sde_fortify_map.xml')


class FortifyIntegrator(BaseIntegrator):
    TOOL_NAME = "fortify"

    def __init__(self, config):
        supported_file_types = ["xml", "fpr", "fvdl"]
        super(FortifyIntegrator, self).__init__(config, self.TOOL_NAME, supported_file_types, DEFAULT_MAPPING_FILE)

    def parse_report_file(self, report_file, report_type):
        if report_type == 'xml':
            importer = FortifyReportImporter()
        elif report_type == 'fpr':
            importer = FortifyFPRImporter()
        elif report_type == 'fvdl':
            importer = FortifyFVDLImporter()
        else:
            raise FortifyIntegrationError("Unsupported file type (%s)" % report_type)

        importer.parse(report_file)

        return importer.raw_findings, importer.report_id

    def _make_finding(self, item):
        return {'weakness_id': item['id'], 'description': item['description'], 'count': item['count']}

    def generate_findings(self):
        return [self._make_finding(item) for item in self.raw_findings]
