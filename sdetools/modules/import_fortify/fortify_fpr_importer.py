import os

import zipfile
from sdetools.sdelib import commons
from sdetools.modules.import_fortify.fortify_base_importer import FortifyBaseImporter
from sdetools.modules.import_fortify.fortify_fvdl_importer import FortifyFVDLImporter

class FortifyFPRImporter(FortifyBaseImporter):

    def __init__(self):
        super(FortifyFPRImporter, self).__init__()

    def parse(self, fpr_file):
        try:
            fpr_file = zipfile.ZipFile(fpr_file, "r")
        except Exception, e:
            raise e

        importer = FortifyFVDLImporter()
        fvdl_xml = None
        try:
            fvdl_xml = fpr_file.read('audit.fvdl')
        except Exception, e:
            raise e

        importer.parse_string(fvdl_xml)

        self.report_id = importer.report_id
        self.raw_findings = importer.raw_findings