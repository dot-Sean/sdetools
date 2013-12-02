from sdetools.analysis_integration.base_integrator import BaseZIPImporter
from sdetools.modules.import_fortify.fortify_fvdl_importer import FortifyFVDLImporter
from sdetools.modules.import_fortify.fortify_audit_importer import FortifyAuditImporter


class FortifyFPRImporter(BaseZIPImporter):

    ANALYSIS_BLACKLIST = []  # Filter out issues based on this list of analysis statuses

    def __init__(self, blacklist=[]):
        super(FortifyFPRImporter, self).__init__()
        self.register_importer('audit.xml', FortifyAuditImporter())
        self.register_importer('audit.fvdl', FortifyFVDLImporter())
        self.ANALYSIS_BLACKLIST = blacklist

    def parse(self, fpr_file):

        self.findings = []
        self.process_archive(fpr_file)

        # If we have no audit details or blacklists then we're done
        audit_findings = self.IMPORTERS['audit.xml'].findings
        if not audit_findings or not self.ANALYSIS_BLACKLIST:
            self.findings = self.IMPORTERS['audit.fvdl'].findings
            return
        print audit_findings
        self.id = self.IMPORTERS['audit.xml'].id

        # remove issues that match our blacklist
        for vulnerability_instance in self.IMPORTERS['audit.fvdl'].findings:
            instance_id = vulnerability_instance['instance_id']
            print "checking %s " % instance_id
            if instance_id in audit_findings and audit_findings[instance_id] in self.ANALYSIS_BLACKLIST:
                # skip this vulnerability
                print "skip!"
                continue
            else:
                print "keep!"
                self.findings.append(vulnerability_instance)