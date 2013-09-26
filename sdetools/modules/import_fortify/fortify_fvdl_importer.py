from sdetools.analysis_integration.base_integrator import BaseXMLImporter, BaseContentHandler


class FVDLXMLContent(BaseContentHandler):

    def __init__(self):
        self.saw_fvdl_node = False
        self.saw_build_node = False
        self.in_build_node = False
        self.in_build_build_id_node = False
        self.in_vuln_node = False
        self.in_vuln_class_info_node = False
        self.in_vuln_class_info_type_node = False
        self.raw_findings = []
        self.report_id = ""

    def valid_content_detected(self):
        return self.saw_build_node

    def processingInstruction(self, target, data):
        pass

    def startElement(self, name, attrs):
        if name == 'FVDL':
            self.saw_fvdl_node = True
        if name == 'Vulnerability':
            self.in_vuln_node = True
        elif self.in_vuln_node and name == 'ClassInfo':
            self.in_vuln_class_info_node = True
        elif self.in_vuln_class_info_node and name == 'Type':
            self.in_vuln_class_info_type_node = True
        elif self.saw_fvdl_node and name == 'Build':
            self.saw_build_node = True
            self.in_build_node = True
        elif self.in_build_node and name == 'BuildID':
            self.in_build_build_id_node = True

    def characters(self, data):
        if self.in_vuln_class_info_type_node:
            entry = {}
            entry['id'] = data
            entry['count'] = 1
            entry['description'] = data
            self.raw_findings.append(entry)
        elif self.in_build_build_id_node:
            self.report_id = data

    def endElement(self, name):
        if self.in_vuln_node and name == 'Vulnerability':
            self.in_vuln_node = False
        elif self.in_vuln_class_info_node and name == 'ClassInfo':
            self.in_vuln_class_info_node = False
        elif self.in_vuln_class_info_type_node and name == 'Type':
            self.in_vuln_class_info_type_node = False
        elif self.in_build_build_id_node and name == 'BuildID':
            self.in_build_build_id_node = False
        elif self.in_build_node and name == 'Build':
            self.in_build_node = False


class FortifyFVDLImporter(BaseXMLImporter):

    def _get_content_handler(self):
        return FVDLXMLContent()
