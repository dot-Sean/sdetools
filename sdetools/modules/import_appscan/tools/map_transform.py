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
        self.task_map = {}
        self.task_map['186'] = []
        self.task_map['193'] = [{'check_id': '*', 'category_id': '', 'check_name': 'Unmapped Check'}]


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
                if category_mapping.has_key(category.attributes['id'].value):
                    tasks = category_mapping[category.attributes['id'].value]
                tasks.append(task.attributes['id'].value)
                category_mapping[category.attributes['id'].value] = tasks

        self.mapping = category_mapping

    def load_custom_mapping_from_xml(self, mapping_file):
        try:
            base = minidom.parse(mapping_file)
        except Exception, e:
            raise MappingError("An error occurred opening mapping file '%s': %s" % (mapping_file, e))

        for task in base.getElementsByTagName('task'):
            task_id = task.attributes['id'].value
            if task_id not in self.base_tasks.keys():
                self.base_tasks[task_id] = task
            task_checks = []
            if task_id in self.task_map.keys():
                task_checks = self.task_map[task_id]
            for check_row in task.getElementsByTagName('weakness'):
                check = {}
                check['check_id'] = check_row.attributes['id'].value
                check['category_id'] = check_row.attributes['category'].value
                check['check_name'] = check_row.attributes['title'].value
                check['check_name'] = check['check_name'].replace('"', '&quot;')
                check['check_name'] = check['check_name'].replace('&', '&amp;')

                if not self.check_in_list(task_checks, check['check_id']):
                    task_checks.append(check)

            self.task_map[task_id] = task_checks

    def load_weaknesses_from_xml(self, checks_file):
        try:
            base = minidom.parse(checks_file)
        except Exception, e:
            raise MappingError("An error occurred opening checks file '%s': %s" % (checks_file, e))

        category_checks = {}
        for check_row in base.getElementsByTagName('ROW'):
            check = {}
            check['check_id'] = check_row.attributes['ID'].value
            check['category_id'] = check_row.attributes['THREATCLASSID'].value
            check['check_name'] = check_row.attributes['ADVISORYID'].value
            check['third_party'] = check_row.attributes['THIRDPARTY'].value == '1'

            if check['third_party']:
                self.task_map['186'].append(check)
                continue

            checks = []
            if category_checks.has_key(check['category_id']):
                checks = category_checks[check['category_id']]
            checks.append(check)

            category_checks[check['category_id']] = checks

            if not check['check_id'] in self.checks:
                self.checks.append(check['check_id'])
            
        self.category_checks = category_checks

    def remap(self):

        keys = sorted(self.category_checks.iterkeys())
        for cwe in keys:
            if self.mapping.has_key(cwe):
                tasks = self.mapping[cwe]
                for task in tasks:
                    task_checks = []
                    if self.task_map.has_key(task):
                        task_checks = self.task_map[task]
                    for check in self.category_checks[cwe]:

                        # If the check is assigned elsewhere - move on
                        if self.check_mapped(self.task_map, check['check_id']):
                            continue

                        task_mapping_found = False
                        for task_check in task_checks:
                            if task_check['check_id'] == check['check_id']:
                                task_mapping_found = True
                        if not task_mapping_found:
                            task_checks.append(check)
                    self.task_map[task] = task_checks
            else:  # map to 193
                task_mapping_found = False
                task_checks = []
                task = '193'
                if task in self.task_map.keys():
                    task_checks = self.task_map[task]
                for check in self.category_checks[cwe]:

                    # If the check is assigned elsewhere do not put it in the catch-all task
                    if self.check_mapped(self.task_map, check['check_id']):
                        continue

                    for chk in task_checks:
                        if chk['check_id'] == check['check_id']:
                            task_mapping_found = True
                    if not task_mapping_found:
                        task_checks.append(check)
                self.task_map[task] = task_checks

    def check_in_list(self, a_list, check_id):
        for item in a_list:
            if item['check_id'] == check_id:
                return True
        return False

    def check_mapped(self, task_map, check_id):
        keys = task_map.iterkeys()

        for task_id in keys:
            task_checks = task_map[task_id]
            if self.check_in_list(task_checks, check_id):
                return True
        return False

    def output_mapping(self, file_name):
        fp = open(file_name, "w")
        keys = sorted(self.task_map.iterkeys())
        fp.write('<mapping>\n')
        for task_id in keys:
            task_checks = self.task_map[task_id]
            confidence = "low"
            """
            if 'confidence' in self.base_tasks[task_id].attributes.keys():
                confidence = self.base_tasks[task_id].attributes['confidence'].value
            """
            fp.write('\t<task id="%s" title="%s" confidence="%s">\n'%
                    (task_id, self.base_tasks[task_id].attributes['title'].value, confidence))
            task_checks = sorted(task_checks)
            for check in task_checks:
                fp.write('\t\t<weakness type="check" id="%s" category="%s" title="%s" />\n'% (check['check_id'], check['category_id'], check['check_name']))
            fp.write('\t</task>\n')
        fp.write('</mapping>\n')
        fp.close()

    def find_missing_checks(self):
        missing_checks = False
        for check in self.checks:
            if not self.check_mapped(self.task_map, check):
                print "*** Check %s is not mapped" % check
                missing_checks = True
        return missing_checks

def main(argv):

    usage = "Usage: %s <category mapping> <custom map> <appscan checks> <appscan map>\n" % (argv[0])

    if len(argv) == 2 and argv[1] == 'help':
        print usage
        print "category mapping: (input) docs/appscan/sde_appscan_standard_category_map.xml"
        print "custom map: (input) Task->WebInspect check mapping in xml format [i.e. custom_webinspect_map.xml]"
        print "appscan checks: (input) AppScan checks in xml format [i.e. appscan_checks.xml]"
        print "appscan map: (output) AppScan map file"
        sys.exit(0)
    elif len(argv) < 4:
        print usage
        sys.exit(1)

    base = Mapping()

    print "Loading category map..."
    base.load_base_mapping_from_xml(argv[1])
    
    print "Loading custom map..."
    base.load_custom_mapping_from_xml(argv[2])

    print "Loading AppScan Checks..."
    base.load_weaknesses_from_xml(argv[3])
    
    print "Re-mapping Checks..."
    base.remap()
    
    print "Validating..."
    if False and base.find_missing_checks():
        print "Aborted"
        sys.exit(1)

    print "Outputting AppScan map to %s..." % argv[4]
    base.output_mapping(argv[4])

    print "Done."        

if __name__ == "__main__":
    main(sys.argv)

