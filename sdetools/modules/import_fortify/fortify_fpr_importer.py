from sdetools.analysis_integration.base_integrator import BaseZIPImporter
from sdetools.modules.import_fortify.fortify_fvdl_importer import FortifyFVDLImporter


class FortifyFPRImporter(BaseZIPImporter):
    ARCHIVED_FILE_NAME = "audit.fvdl"

    def __init__(self):
        super(FortifyFPRImporter, self).__init__()

    def parse(self, fpr_file):

        self.process_archive(fpr_file, FortifyFVDLImporter())
