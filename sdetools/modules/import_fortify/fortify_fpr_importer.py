import os
import zipfile

from sdetools.sdelib import commons
from sdetools.analysis_integration.base_integrator import BaseImporter
from sdetools.modules.import_fortify.fortify_fvdl_importer import FortifyFVDLImporter
from sdetools.modules.import_fortify.fortify_integration_error import FortifyIntegrationError


class FortifyFPRImporter(BaseImporter):
    AUDIT_FILE = "audit.fvdl"
    MAX_SIZE_IN_MB = 50  # Maximum FVDL size in MB

    def __init__(self):
        super(FortifyFPRImporter, self).__init__()

    def parse(self, fpr_file):
        try:
            fpr_file = zipfile.ZipFile(fpr_file, "r")
        except zipfile.BadZipfile, e:
            raise FortifyIntegrationError("Error opening file (Bad file) %s" % (fpr_file))
        except zipfile.LargeZipFile, e:
            raise FortifyIntegrationError("Error opening file (File too large) %s" % (fpr_file))

        importer = FortifyFVDLImporter()

        try:
            file_info = fpr_file.getinfo(self.AUDIT_FILE)
        except KeyError, ke:
            raise FortifyIntegrationError("File (%s) not found in archive %s" % (self.AUDIT_FILE, fpr_file))

        if file_info.file_size > self.MAX_SIZE_IN_MB * 1024 * 1024:
            raise FortifyIntegrationError("File %s is larger than %s MB: %d bytes" %
                    (self.AUDIT_FILE, self.MAX_SIZE_IN_MB, file_info.file_size))

        # Python 2.6+ can open a ZIP file entry as a stream
        if hasattr(fpr_file, 'open'):
            try:
                fvdl_file = fpr_file.open(self.AUDIT_FILE)
            except KeyError, ke:
                raise FortifyIntegrationError("File (%s) not found in archive %s" % (self.AUDIT_FILE, fpr_file))

            importer.parse_file(fvdl_file)

        # Python 2.5 and prior must open the file into memory
        else:
            fvdl_xml = fpr_file.read(self.AUDIT_FILE)
            importer.parse_string(fvdl_xml)

        self.report_id = importer.report_id
        self.raw_findings = importer.raw_findings
