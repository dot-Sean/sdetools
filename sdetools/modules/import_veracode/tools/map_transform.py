#!/usr/bin/python
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from xml.dom import minidom

class MappingError(Exception):
    pass

class Mapping:
    def __init__(self):
        self.mapping = {}

    def load_mapping_from_xml(self, mapping_file):
        try:
            base = minidom.parse(mapping_file)
        except Exception:
            raise MappingError("An error occured opening mapping file '%s'" % mapping_file)

        cwe_mapping = {}
        for task in base.getElementsByTagName('task'):
            for cwe in task.getElementsByTagName('cwe'):
                 tasks = []
                 if (cwe_mapping.has_key(cwe.attributes['id'].value)):
                     tasks = cwe_mapping[cwe.attributes['id'].value]
                 tasks.append(task.attributes['id'].value)
                 cwe_mapping[cwe.attributes['id'].value] = tasks

        self.mapping = cwe_mapping

    def output_mapping(self):
        keys = sorted(self.mapping.iterkeys())
        for cwe in keys:
            tasks = self.mapping[cwe]
            print '<cwe id="%s">'%cwe
            for task in tasks:
                print '\t<task id="%s"/>'%task
            print '</cwe'
def main(argv):
    base = Mapping()
    base.load_mapping_from_xml(argv[1])

    base.output_mapping()

if __name__ == "__main__":
    main(sys.argv)

