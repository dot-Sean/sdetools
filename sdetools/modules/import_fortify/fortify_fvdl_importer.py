import os
import re
import xml.sax

from sdetools.sdelib import commons
from sdetools.analysis_integration.base_integrator import BaseImporter

class FVDLXMLContent(xml.sax.handler.ContentHandler):
    def __init__(self):
        self.in_build_node = False
        self.in_build_build_id_node = False
        self.in_vuln_node = False
        self.in_vuln_class_info_node = False
        self.in_vuln_class_info_type_node = False
        self.raw_findings = []
        self.report_id = ""

    def processingInstruction(self, target, data):
        pass

    def startElement(self, name, attrs):
        if name == 'Vulnerability':
            self.in_vuln_node = True
        elif self.in_vuln_node and name == 'ClassInfo':
            self.in_vuln_class_info_node = True
        elif self.in_vuln_class_info_node and name == 'Type':
            self.in_vuln_class_info_type_node = True
        elif name == 'Build':
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
        if self.in_vuln_class_info_node and name == 'ClassInfo':
            self.in_vuln_class_info_node = False
        if self.in_vuln_class_info_type_node and name == 'Type':
            self.in_vuln_class_info_type_node = False
        elif self.in_build_build_id_node and name == 'BuildID':
            self.in_build_build_id_node = False
        elif self.in_build_node and name == 'Build':
            self.in_build_node = False
    
class FortifyFVDLImporter(BaseImporter):

    def __init__(self):
        super(FortifyFVDLImporter, self).__init__()

    def parse(self, fvdl_file):
        try:    
            self.parse_file(open(fvdl_file, 'rb'))
        except Exception, e:
            raise Exception("Error opening FVDL file (%s): %s" % (fvdl_file, e))

    def parse_file(self, fvdl_file):
        FVDLReader = FVDLXMLContent()
        try:    
            parser = xml.sax.make_parser()
            parser.setContentHandler(FVDLReader)
            parser.parse(fvdl_file)
        except Exception, e:
            raise Exception("Error opening FVDL file (%s): %s" % (fvdl_file, e))
        
        self.raw_findings = FVDLReader.raw_findings
        self.report_id = FVDLReader.report_id

    def parse_string(self, fvdl_xml):
        FVDLReader = FVDLXMLContent()
        try:    
            xml.sax.parseString(fvdl_xml, FVDLReader)
        except Exception, e:
            raise e
        
        self.raw_findings = FVDLReader.raw_findings
        self.report_id = FVDLReader.report_id
    
