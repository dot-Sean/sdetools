from sdetools.analysis_integration.base_integrator import BaseZIPImporter
from sdetools.modules.import_webinspect.webinspect_xml_importer import WebInspectXMLImporter


class WebInspectFPRImporter(BaseZIPImporter):

    def __init__(self):
        super(WebInspectFPRImporter, self).__init__()
        self.register_importer('webinspect.xml', WebInspectXMLImporter())

    def parse(self, fpr_file):

        self.process_archive(fpr_file)
        self.findings = self.IMPORTERS['webinspect.xml'].findings
        self.id = self.IMPORTERS['webinspect.xml'].id