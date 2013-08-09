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

    def parse(self, fpr_file_name):
        try:
            fpr_fd = zipfile.ZipFile(fpr_file_name, "r")
        except zipfile.BadZipfile, e:
            raise FortifyIntegrationError("Error opening file (Bad file) %s" % (fpr_file_name))
        except zipfile.LargeZipFile, e:
            raise FortifyIntegrationError("Error opening file (File too large) %s" % (fpr_file_name))

        importer = FortifyFVDLImporter()

        try:
            file_info = fpr_fd.getinfo(self.AUDIT_FILE)
        except KeyError, ke:
            raise FortifyIntegrationError("File (%s) not found in archive %s" % (self.AUDIT_FILE, fpr_file_name))

        if file_info.file_size > self.MAX_SIZE_IN_MB * 1024 * 1024:
            raise FortifyIntegrationError("File %s is larger than %s MB: %d bytes" %
                    (self.MAX_SIZE_IN_MB, self.AUDIT_FILE, file_info.file_size))

        # Python 2.6+ can open a ZIP file entry as a stream
        if hasattr(fpr_fd, 'open'):
            try:
                fvdl_file = fpr_fd.open(self.AUDIT_FILE)
            except KeyError, ke:
                raise FortifyIntegrationError("File (%s) not found in archive %s" % (self.AUDIT_FILE, fpr_file_name))

            importer.parse_file(fvdl_file)

            fvdl_file.close()

        # Python 2.5 and prior must open the file into memory
        else:
            fvdl_xml = fpr_fd.read(self.AUDIT_FILE)
            importer.parse_string(fvdl_xml)

        fpr_fd.close()

        self.report_id = importer.report_id
        self.raw_findings = importer.raw_findings
