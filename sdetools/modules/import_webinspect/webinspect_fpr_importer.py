from sdetools.analysis_integration.base_integrator import BaseZIPImporter
from sdetools.modules.import_webinspect.webinspect_xml_importer import WebInspectXMLImporter

class WebInspectFPRImporter(BaseZIPImporter):
    ARCHIVED_FILE_NAME = "webinspect.xml"

    def __init__(self):
        super(WebInspectFPRImporter, self).__init__()

    def parse(self, fpr_file):

        self.process_archive(fpr_file, WebInspectXMLImporter())
