from sdetools.analysis_integration.base_integrator import BaseXMLImporter, BaseContentHandler


class AppScanEnterpriseXMLContent(BaseContentHandler):
    def __init__(self):
        self.saw_app_scan_node = False
        self.in_report_node = False  # top-level node
        self.in_report_control_node = False
        self.in_report_control_row_node = False
        self.in_report_control_row_issue_type_node = False
        self.findings = []
        self.count = 0
        self.id = ""
        self.check_id = ""

    def valid_content_detected(self):
        return self.saw_app_scan_node

    def processingInstruction(self, target, data):
        pass

    def startElement(self, name, attrs):
        if name == 'report':
            self.in_report_node = True
            self.saw_app_scan_node = True
        elif self.in_report_node and name == 'control':
            self.in_report_control_node = True
        elif self.in_report_control_node and name == 'row':
            self.in_report_control_row_node = True
        elif self.in_report_control_row_node and name == 'issue_type_name':
            self.in_report_control_row_issue_type_node = True
            self.saw_app_scan_node = True

    def characters(self, data):
        if self.in_report_control_row_issue_type_node:
            entry = {}
            entry['id'] = data
            entry['count'] = 1
            entry['description'] = data

            self.findings.append(entry)
            
            # reset
            self.count = 0
            self.check_id = ""

    def endElement(self, name):
        if self.in_report_node and name == 'control':
            self.in_report_control_node = False
        elif self.in_report_control_node and name == 'row':
            self.in_report_control_row_node = False
        elif self.in_report_control_row_node and name == 'issue_type_name':
            self.in_report_control_row_issue_type_node = False


class AppScanEnterpriseXMLImporter(BaseXMLImporter):

    def __init__(self):
        super(AppScanEnterpriseXMLImporter, self).__init__()
        self.edition = 'enterprise'

    def _get_content_handler(self):
        return AppScanEnterpriseXMLContent()