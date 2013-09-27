#!/usr/bin/python
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from xml.dom import minidom

class MappingError(Exception):
    pass


class Mapping:
    def __init__(self):
        self.cwe_tuple_list = []

    def load_cwe_tuples_from_xml(self, weakness_file):
        try:
            base = minidom.parse(weakness_file)
        except Exception, e:
            raise MappingError("An error occurred opening mapping file '%s': %s" % (weakness_file, e))

        cwe_tuple = []
        last_check = None
        for weakness_row in base.getElementsByTagName('Table1'):
            check = weakness_row.getElementsByTagName('CheckID')[0].firstChild.data
            cwe = weakness_row.getElementsByTagName('CWE')[0].firstChild.data
            cwe_desc = weakness_row.getElementsByTagName('CWE_Desc')[0].firstChild.data
            if last_check != check:
                last_check = check
                cwe_tuple = sorted(cwe_tuple)
                if cwe_tuple and cwe_tuple not in self.cwe_tuple_list:
                    self.cwe_tuple_list.append(cwe_tuple)
                cwe_tuple = []
            cwe_tuple.append({'cwe': cwe, 'desc': cwe_desc})

    def output_mapping(self, file_name):
        fp = open(file_name, "w")
        fp.write('<tuples count="%d">\n' % len(self.cwe_tuple_list))
        for cwe_tuple in self.cwe_tuple_list:
            fp.write('\t<tuple>\n')
            for cwe_entry in cwe_tuple:
                fp.write('\t\t<cwe id="%s" title="%s" />\n' % (cwe_entry['cwe'], cwe_entry['desc']))
            fp.write('\t</tuple>\n')
        fp.write('</tuples>\n')
        fp.close()

def main(argv):

    usage = "Usage: %s <webinspect checks> <cwe_tuples>\n" % (argv[0])

    if len(argv) == 2 and argv[1] == 'help':
        print usage
        print "webinspect checks: (input) WebInspect checks in xml format [i.e. webinspect_checks.xml]"
        sys.exit(0)
    elif len(argv) < 3:
        print usage
        sys.exit(1)

    base = Mapping()

    print "Loading WebInspect Checks..."    
    base.load_cwe_tuples_from_xml(argv[1])
    base.output_mapping(argv[2])
    print "Done."        

if __name__ == "__main__":
    main(sys.argv)

