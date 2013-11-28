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
        config.add_custom_option("report_file", "Common separated list of Fortify Report Files", "x", None)
        config.add_custom_option("report_type", "Fortify Report Type: xml|fpr|fvdl|auto", default="auto")
        super(FortifyIntegrator, self).__init__(config, DEFAULT_MAPPING_FILE)
        self.raw_findings = []
        self.importer = None
        self.report_ids = []

    def parse(self):
        if not self.config['report_file']:
            raise UsageError("Missing configuration option 'report_file'")
        else:
            # Comma delimited report files
            if isinstance(self.config['report_file'], basestring):
                self.config.process_list_config('report_file')
                report_files = self.config['report_file']
            else:
                report_files = [self.config['report_file']]

        for report_file in report_files:
            if self.config['report_type'] == 'auto':
                if not isinstance(report_file, basestring):
                    raise UsageError("On auto-detect mode, the file name needs to be specified.")
                file_name, file_extension = os.path.splitext(report_file)
                report_type = file_extension[1:]
            else:
                report_type = self.config['report_type']

            if report_type == 'xml':
                self.importer = FortifyReportImporter()
            elif report_type == 'fpr':
                self.importer = FortifyFPRImporter()
            elif report_type == 'fvdl':
                self.importer = FortifyFVDLImporter()
            else:
                raise FortifyIntegrationError("Unsupported file type (%s)" % report_type)

            self.importer.parse(report_file)
            self.raw_findings.extend(self.importer.raw_findings)

            if self.importer.report_id:
                self.report_ids.append(self.importer.report_id)
            else:
                self.emit.info("Report ID not found in report: Using default.")
        self.report_id = ', '.join(self.report_ids)

    def _make_finding(self, item):
        return {'weakness_id': item['id'], 'description': item['description'], 'count': item['count']}

    def generate_findings(self):
        return [self._make_finding(item) for item in self.raw_findings]
