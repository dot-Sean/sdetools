from sdetools.analysis_integration.base_integrator import BaseXMLImporter, BaseContentHandler


class AuditXMLContent(BaseContentHandler):

    TRIAGE_TAG_ID = '87f2364f-dcd4-49e6-861d-f8d3f351686b'  # Specific tag for triage status

    def __init__(self):
        self.saw_audit_node = False
        self.in_audit_node = False
        self.saw_project_info_node = False
        self.saw_project_info_name_node = False
        self.in_project_info_node = False
        self.in_project_info_name_node = False
        self.in_project_info_version_node = False
        self.saw_issue_list_node = False
        self.in_issue_list_node = False
        self.in_issue_node = False
        self.saw_tag_node = False
        self.in_triage_node = False
        self.in_triage_value_node = False
        self.project_name = ""
        self.project_version = ""
        self.findings = {}
        self.current_instance = None
        self.depth = 0

    def valid_content_detected(self):
        return self.saw_project_info_node

    def processingInstruction(self, target, data):
        pass

    def startElement(self, name, attrs):

        self.depth += 1

        name_split = name.split(':')
        if len(name_split) == 2:
            prefix, node_name = name_split
        else:
            node_name = name_split[0]

        if node_name == 'Audit':
            self.saw_audit_node = True
            self.in_audit_node = True
        elif self.in_audit_node and node_name == 'ProjectInfo':
            self.saw_project_info_node = True
            self.in_project_info_node = True
        elif self.in_project_info_node and node_name == 'Name':
            self.in_project_info_name_node = True
        elif self.in_project_info_node and node_name == 'ProjectVersionName':
            self.in_project_info_version_node = True
        elif self.in_audit_node and node_name == 'IssueList':
            self.saw_issue_list_node = True
            self.in_issue_list_node = True
        elif self.in_issue_list_node and node_name == 'Issue':
            self.in_issue_node = True
            self.current_instance = attrs['instanceId']
        # Ignore Tags from the audit trail
        elif self.in_issue_node and node_name == 'Tag' and self.depth == 4:
            if attrs['id'] == self.TRIAGE_TAG_ID:
                self.in_triage_node = True
        elif self.in_triage_node and node_name == 'Value':
            self.in_triage_value_node = True

    def characters(self, data):
        if self.in_project_info_name_node:
            self.project_name = data
        elif self.in_project_info_version_node:
            self.project_version = data
        elif self.in_triage_value_node:
            if self.current_instance:
                self.findings[self.current_instance] = data

    def endElement(self, name):

        self.depth -= 1

        name_split = name.split(':')
        if len(name_split) == 2:
            prefix, node_name = name_split
        else:
            node_name = name_split[0]

        if self.in_project_info_node and node_name == 'ProjectInfo':
            self.in_project_info_node = False
            self.id = "%s %s" % (self.project_name, self.project_version)
        elif self.in_project_info_name_node and node_name == 'Name':
            self.in_project_info_name_node = False
        elif self.in_project_info_version_node and node_name == 'ProjectVersionName':
            self.in_project_info_version_node = False
        elif self.in_issue_list_node and node_name == 'IssueList':
            self.in_issue_list_node = False
        elif self.in_issue_node and node_name == 'Issue':
            self.in_issue_node = False
            self.current_instance = None
        elif self.in_triage_node and node_name == 'Tag':
            self.in_triage_node = False
        elif self.in_triage_value_node and node_name == 'Value':
            self.in_triage_value_node = False

class FortifyAuditImporter(BaseXMLImporter):

    def _get_content_handler(self):
        return AuditXMLContent()
