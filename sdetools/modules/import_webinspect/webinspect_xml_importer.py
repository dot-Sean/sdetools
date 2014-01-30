from sdetools.analysis_integration.base_integrator import BaseXMLImporter, BaseContentHandler


class WebInspectXMLContent(BaseContentHandler):
    def __init__(self):
        self.saw_sessions_node = False
        self.in_issue_node = False
        self.in_vuln_node = False
        self.in_issue_name_node = False
        self.in_session_node = False
        self.in_url_node = False
        self.findings = []
        self.report_id = ""
        self.check_id = 0
        self.check_name_found = False

    def valid_content_detected(self):
        return self.saw_sessions_node

    def processingInstruction(self, target, data):
        pass

    def startElement(self, name, attrs):
        if name == 'Sessions':
            self.saw_sessions_node = True
        elif name == 'Issue':
            self.in_issue_node = True
        elif name == 'VulnerabilityID':
            self.in_vuln_node = True
        elif self.in_issue_node and not self.check_name_found and name == 'Name':
            self.in_issue_name_node = True
        elif name == 'Session':
            self.in_session_node = True
        elif self.in_session_node and name == 'Host':
            self.in_url_node = True

    def characters(self, data):
        if self.in_issue_node and self.in_vuln_node:
            self.check_id = data
        elif self.in_issue_node and self.in_issue_name_node:
            entry = {}
            entry['id'] = self.check_id
            entry['count'] = 1
            entry['type'] = 'check'
            entry['description'] = data
            self.findings.append(entry)
            self.check_id = 0
            self.check_name_found = True
        elif self.in_session_node and self.in_url_node:
            self.id = data

    def endElement(self, name):
        if self.in_issue_node and name == 'Issue':
            self.in_issue_node = False
            self.check_name_found = False
        elif self.in_issue_node and self.in_vuln_node and name == 'VulnerabilityID':
            self.in_vuln_node = False
        elif self.in_issue_node and self.in_issue_name_node and name == 'Name':
            self.in_issue_name_node = False
        elif self.in_session_node and name == 'Session':
            self.in_session_node = False
        elif self.in_session_node and self.in_url_node and name == 'Host':
            self.in_url_node = False
    
class WebInspectXMLImporter(BaseXMLImporter):

    def __init__(self):
        super(WebInspectXMLImporter, self).__init__()

    def _get_content_handler(self):
        return WebInspectXMLContent()