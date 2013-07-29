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
        for weakness_row in base.getElementsByTagName('Table1'):
            weakness = {}
            weakness['check_id'] = weakness_row.getElementsByTagName('CheckID')[0].firstChild.data
            weakness['check_name'] = weakness_row.getElementsByTagName('CheckName')[0].firstChild.data
            weakness['check_name'] = weakness['check_name'].replace('"','&quot;')
            weakness['check_name'] = weakness['check_name'].replace('&','&amp;')
            
            cwe = weakness_row.getElementsByTagName('CWE')[0].firstChild.data
            weakness['cwe_desc'] = weakness_row.getElementsByTagName('CWE_Desc')[0].firstChild.data
            weakness['cwe_desc'] = weakness['cwe_desc'].replace('"','&quot;')
            weakness['cwe_desc'] = weakness['cwe_desc'].replace('&','&amp;')
            weakness['cwe_id'] = cwe[4:]
            
            weaknesses = []
            if (cwe_weaknesses.has_key(weakness['cwe_id'])):
                weaknesses = cwe_weaknesses[weakness['cwe_id']]
            weaknesses.append(weakness)
            cwe_weaknesses[weakness['cwe_id']] = weaknesses

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
                print '\t\t<weakness type="check" id="%s" name="%s" cwe="%s" title="%s"/>'% (weakness['check_id'], weakness['check_name'], weakness['cwe_id'], weakness['cwe_desc'])
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

