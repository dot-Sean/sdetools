#!/usr/bin/python
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from xml.dom import minidom

class MappingError(Exception):
    pass

class Mapping:
    def __init__(self):
        self.mapping = {}
        self.cwe_weaknesses = {}
        self.base_tasks = {}

    def load_base_mapping_from_xml(self, mapping_file):
        try:
            base = minidom.parse(mapping_file)
        except Exception, e:
            raise MappingError("An error occured opening mapping file '%s': %s" % (mapping_file, e))

        cwe_mapping = {}
        for task in base.getElementsByTagName('task'):
            self.base_tasks[ task.attributes['id'].value ] = task
            for cwe in task.getElementsByTagName('weakness'):
                 tasks = []
                 if (cwe_mapping.has_key(cwe.attributes['id'].value)):
                     tasks = cwe_mapping[cwe.attributes['id'].value]
                 tasks.append(task.attributes['id'].value)
                 cwe_mapping[cwe.attributes['id'].value] = tasks

        self.mapping = cwe_mapping

    def load_weaknesses_from_xml(self, weakness_file):
        try:
            base = minidom.parse(weakness_file)
        except Exception, e:
            raise MappingError("An error occured opening mapping file '%s': %s" % (weakness_file, e))

        cwe_weaknesses = {}
        for weakness in base.getElementsByTagName('weakness'):
             weaknesses = []
             if (cwe_weaknesses.has_key(weakness.attributes['cwe'].value)):
                 weaknesses = cwe_weaknesses[weakness.attributes['cwe'].value]
             weaknesses.append(weakness)
             cwe_weaknesses[weakness.attributes['cwe'].value] = weaknesses

        self.cwe_weaknesses = cwe_weaknesses
        
    def remap(self):
        task_map = {}
        nomap = {}

        keys = sorted(self.cwe_weaknesses.iterkeys())
        for cwe in keys:
            if self.mapping.has_key(cwe):
                tasks = self.mapping[cwe]
                for task in tasks:
                    weaknesses = []
                    if task_map.has_key(task):
                        weaknesses = task_map[task]
                    for wk in self.cwe_weaknesses[cwe]:
                        weaknesses.append(wk)
                    task_map[task] = weaknesses
            else: #map to 193
                    weaknesses = []
                    task = '193'
                    if task_map.has_key(task):
                        weaknesses = task_map[task]
                    for wk in self.cwe_weaknesses[cwe]:
                        weaknesses.append(wk)
                    task_map[task] = weaknesses
        self.task_map = task_map

    def output_mapping(self):
        keys = sorted(self.task_map.iterkeys())
        print '<mapping>'
        for task_id in keys:
            weaknesses = self.task_map[task_id]
            print '\t<task id="%s" title="%s">'%(task_id, self.base_tasks[task_id].attributes['title'].value)
            weaknesses = sorted(weaknesses)
            for weakness in weaknesses:
                print '\t\t<weakness type="check" id="%s" name="%s" cwe="%s" title="%s"/>'% (weakness.attributes['id'].value, weakness.attributes['name'].value, weakness.attributes['cwe'].value, weakness.attributes['title'].value)
            print '\t</task>'
        print '</mapping>'            
def main(argv):
    base = Mapping()
    base.load_base_mapping_from_xml(argv[1])
    base.load_weaknesses_from_xml(argv[2])
    base.remap()
    base.output_mapping()

if __name__ == "__main__":
    main(sys.argv)

