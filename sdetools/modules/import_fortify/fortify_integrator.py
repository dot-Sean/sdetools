import os

from sdetools.sdelib.commons import media_path, UsageError
from sdetools.analysis_integration.base_integrator import BaseIntegrator

from sdetools.modules.import_fortify.fortify_integration_error import FortifyIntegrationError
from sdetools.modules.import_fortify.fortify_report_importer import FortifyReportImporter
from sdetools.modules.import_fortify.fortify_fpr_importer import FortifyFPRImporter
from sdetools.modules.import_fortify.fortify_fvdl_importer import FortifyFVDLImporter
from sdetools.modules.import_fortify.fortify_ssc_importer import FortifySSCImporter

__all__ = ['FortifyIntegrator']

DEFAULT_MAPPING_FILE = os.path.join(media_path, 'fortify', 'sde_fortify_map.xml')


class FortifyIntegrator(BaseIntegrator):
    TOOL_NAME = "fortify"

    def __init__(self, config):
        supported_file_types = ["xml", "fpr", "fvdl"]
        super(FortifyIntegrator, self).__init__(config, self.TOOL_NAME, supported_file_types, DEFAULT_MAPPING_FILE)
    
        self.config.opts.add("import_blacklist", "Do not import issues which have been triaged with these " +
                "statuses (i.e. 'Bad Practice, Not an Issue').", "a", "Not an Issue")
        config.add_custom_option('integration_mode',"Integration mode: (ssc or file)", default='file')
        config.add_custom_option("file_results", "Verification results file", "x", default='')
        config.add_custom_option('ssc_test_connection','Test Fortify SSC Connection Only '
                '(Also checks existence of project and version)', default='False')
        config.add_custom_option('ssc_method','http vs https for Fortify SSC server', default='https')
        config.add_custom_option('ssc_server','Fortify SSC server name or IP', default='')
        config.add_custom_option('ssc_user','Fortify SSC user',default='')
        config.add_custom_option('ssc_pass','Fortify SSC password',default='')
        config.add_custom_option('ssc_authtoken','Fortify SSC authtoken (AnalysisDownloadToken permission)',default='')
        config.add_custom_option('ssc_project_name','Fortify Project name',default='')
        config.add_custom_option('ssc_project_version','Fortify Project version',default='')
        
        self.raw_findings = []
        self.importer = None

    def initialize(self):
        super(FortifyIntegrator, self).initialize()
        self.config.process_list_config('import_blacklist')
        
        if self.config['integration_mode'] == 'ssc':
            self.config.process_boolean_config('ssc_test_connection')

            for config_key in ['ssc_method','ssc_server','ssc_project_name','ssc_project_version']:
                if not self.config[config_key]:
                    raise UsageError("Missing value for option %s" % config_key)

            if not self.config['ssc_authtoken']:
                for config_key in ['ssc_user','ssc_pass']:
                    if not self.config[config_key]:
                        raise UsageError("Missing value for option %s" % config_key)
            
        elif self.config['integration_mode'] == 'file':        
            if not self.config['file_results']:
                raise UsageError("Missing value for option file_results")
        else:
            raise UsageError("Invalid value for integration_mode. Valid values are: ssc or file")

    def parse_report_file(self, report_file, report_type):
        if report_type == 'xml':
            importer = FortifyReportImporter()
        elif report_type == 'fpr':
            importer = FortifyFPRImporter(self.config['import_blacklist'])
        elif report_type == 'fvdl':
            importer = FortifyFVDLImporter()
        else:
            raise FortifyIntegrationError("Unsupported file type (%s)" % report_type)

        importer.parse(report_file)

        self.findings = importer.findings
        self.report_id = importer.id

        return importer.findings, importer.id

    def _make_finding(self, item):
        return {'weakness_id': item['id'], 'description': item['description'], 'count': item['count']}

    def generate_findings(self):
        return [self._make_finding(item) for item in self.findings]
