import os

import zipfile
from sdetools.sdelib import commons
from sdetools.analysis_integration.base_integrator import BaseImporter
from sdetools.modules.import_fortify.fortify_fvdl_importer import FortifyFVDLImporter

class FortifyFPRImporter(BaseImporter):
    AUDIT_FILE = "audit.fvdl"
    MAX_FVDL_SIZE_BYTES = 1024 * 1024 * 20 # Maximum FVDL size in bytes
    def __init__(self):
        super(FortifyFPRImporter, self).__init__()

    def parse(self, fpr_file):
        try:
            fpr_file = zipfile.ZipFile(fpr_file, "r")
        except Exception, e:
            raise e

        importer = FortifyFVDLImporter()
        fvdl_xml = None
        
        # check the audit.fvdl file size before opening
        try:
            info = fpr_file.getinfo(self.AUDIT_FILE)
        except KeyError, ke:
            raise Exception("File (%s) not found in archive %s" % (self.AUDIT_FILE, fpr_file))
            
        if info is None:
            raise Exception("No information found for file %s in %s" % (self.AUDIT_FILE, fpr_file))
        
        if info.file_size > self.MAX_FVDL_SIZE_BYTES:
            raise Exception("File %s is too large (%d bytes)" % (self.AUDIT_FILE, info.file_size))
        
        fvdl_file = fpr_file.open(self.AUDIT_FILE)

        importer.parse_file(fvdl_file)
        self.report_id = importer.report_id
        self.raw_findings = importer.raw_findings