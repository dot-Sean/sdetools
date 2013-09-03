#!/usr/bin/python
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from xml.dom import minidom

class MappingError(Exception):
    pass

class Mapping:
    def __init__(self):
        self.mapping = {}
        self.category_checks = {}
        self.base_tasks = {}
        self.checks = []

    def load_base_mapping_from_xml(self, mapping_file):
        try:
            base = minidom.parse(mapping_file)
        except Exception, e:
            raise MappingError("An error occured opening mapping file '%s': %s" % (mapping_file, e))

        category_mapping = {}
        for task in base.getElementsByTagName('task'):
            self.base_tasks[ task.attributes['id'].value ] = task
            for category in task.getElementsByTagName('category'):
                 tasks = []
                 if (category_mapping.has_key(category.attributes['id'].value)):
                     tasks = category_mapping[category.attributes['id'].value]
                 tasks.append(task.attributes['id'].value)
                 category_mapping[category.attributes['id'].value] = tasks

        self.mapping = category_mapping

    def load_weaknesses_from_xml(self, checks_file):
        try:
            base = minidom.parse(checks_file)
        except Exception, e:
            raise MappingError("An error occured opening checks file '%s': %s" % (checks_file, e))

        category_checks = {}
        for check_row in base.getElementsByTagName('ROW'):
            check = {}
            check['check_id'] = check_row.attributes['ID'].value
            check['category_id'] = check_row.attributes['THREATCLASSID'].value
            check['check_name'] = check_row.attributes['ADVISORYID'].value

            checks = []
            if (category_checks.has_key(check['category_id'])):
                checks = category_checks[check['category_id']]
            checks.append(check)
            category_checks[check['category_id']] = checks

            if not check['check_id'] in self.checks:
                self.checks.append(check['check_id'])
            
        self.category_checks = category_checks
        
    def remap(self):
        task_map = {}

        task_map['193'] = [ {'check_id':'*', 'category_id':"", 'check_name': 'Unmapped Check'} ]

        keys = sorted(self.category_checks.iterkeys())
        for cwe in keys:
            if self.mapping.has_key(cwe):
                tasks = self.mapping[cwe]
                for task in tasks:
                    task_checks = []
                    if task_map.has_key(task):
                        task_checks = task_map[task]
                    for check in self.category_checks[cwe]:
                        task_mapping_found = False
                        for task_check in task_checks:
                            if task_check['check_id'] == check['check_id']:
                                task_mapping_found = True
                        if not task_mapping_found:
                            task_checks.append(check)
                    task_map[task] = task_checks
            else: #map to 193
                    task_mapping_found = False
                    task_checks = []
                    task = '193'
                    if task_map.has_key(task):
                        task_checks = task_map[task]
                    for check in self.category_checks[cwe]:
                        for chk in task_checks:
                            if chk['check_id'] == check['check_id']:
                                task_mapping_found = True
                        if not task_mapping_found:
                            task_checks.append(check)
                    task_map[task] = task_checks
        self.task_map = task_map

    def output_mapping(self, file_name):
        fp = open(file_name, "w")
        keys = sorted(self.task_map.iterkeys())
        fp.write('<mapping weaknesses="%d">\n' % len(self.checks))
        for task_id in keys:
            task_checks = self.task_map[task_id]
            fp.write('\t<task id="%s" title="%s" >\n'%(task_id, self.base_tasks[task_id].attributes['title'].value))
            task_checks = sorted(task_checks)
            for check in task_checks:
                fp.write('\t\t<weakness type="check" id="%s" category="%s" title="%s" />\n'% (check['check_id'], check['category_id'], check['check_name']))
            fp.write('\t</task>\n')
        fp.write('</mapping>\n')
        fp.close()

    def find_missing_checks(self):
        keys = sorted(self.task_map.iterkeys())
        missing_checks = False
        for check in self.checks:
            check_found = False
            for task_id in keys:
                task_checks = self.task_map[task_id]
                for task_check in task_checks:
                    if check == task_check['check_id']:
                         check_found = True
            if not check_found:
                print "*** Check %s is not mapped" % check
                missing_checks = True
        return missing_checks

def main(argv):

    usage = "Usage: %s <category mapping> <appscan checks> <appscan map>\n" % (argv[0])

    if len(argv) == 2 and argv[1] == 'help':
        print usage
        print "category mapping: (input) docs/appscan/sde_appscan_standard_category_map.xml"
        print "appscan checks: (input) AppScan checks in xml format [i.e. appscan_checks.xml]"
        print "appscan map: (output) AppScan map file"
        sys.exit(0)
    elif len(argv) < 4:
        print usage
        sys.exit(1)

    base = Mapping()

    print "Loading Category map..."
    base.load_base_mapping_from_xml(argv[1])
    
    print "Loading AppScan Checks..."    
    base.load_weaknesses_from_xml(argv[2])
    
    print "Re-mapping Checks..."
    base.remap()
    
    print "Validating..."
    if base.find_missing_checks():
        print "Aborted"
        sys.exit(1)
        
    print "Outputting AppScan map to %s..." % argv[3]
    base.output_mapping(argv[3])

    print "Done."        

if __name__ == "__main__":
    main(sys.argv)

