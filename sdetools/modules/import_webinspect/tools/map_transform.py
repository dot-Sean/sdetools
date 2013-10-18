#!/usr/bin/python
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from xml.dom import minidom

class MappingError(Exception):
    pass


class Mapping:
    def __init__(self):
        self.mapping = {}
        self.cwe_checks = {}
        self.base_tasks = {}
        self.checks = []
        self.task_map = {}

        # these are good candidates for CWE mapping
        self.appcheck_group = ['5', '6', '12', '30', '60', '586', '587', '657', '703', '1202', '2039']
        # these should be considered 3rd party - T186
        self.thirdparty_group = ['589', '594', '606']
        self.thirdparty_checks = []

    def load_base_mapping_from_xml(self, mapping_file):
        try:
            base = minidom.parse(mapping_file)
        except Exception, e:
            raise MappingError("An error occurred opening mapping file '%s': %s" % (mapping_file, e))

        cwe_mapping = {}
        for task in base.getElementsByTagName('task'):
            self.base_tasks[task.attributes['id'].value ] = task
            for cwe in task.getElementsByTagName('weakness'):
                tasks = []
                if cwe_mapping.has_key(cwe.attributes['id'].value):
                    tasks = cwe_mapping[cwe.attributes['id'].value]
                tasks.append(task.attributes['id'].value)
                cwe_mapping[cwe.attributes['id'].value] = tasks

        self.mapping = cwe_mapping

    def load_custom_mapping_from_xml(self, mapping_file):
        try:
            base = minidom.parse(mapping_file)
        except Exception, e:
            raise MappingError("An error occurred opening mapping file '%s': %s" % (mapping_file, e))

        for task in base.getElementsByTagName('task'):
            task_id = task.attributes['id'].value

            if task_id not in self.base_tasks:
                self.base_tasks[task_id] = task

            task_checks = []
            if task_id in self.task_map.keys():
                task_checks = self.task_map[task_id]
            for check_row in task.getElementsByTagName('weakness'):
                check = {}
                check['check_id'] = check_row.attributes['id'].value
                check['check_name'] = check_row.attributes['title'].value
                check['check_name'] = check['check_name'].replace('"', '&quot;')
                check['check_name'] = check['check_name'].replace('&', '&amp;')

                if not self.check_in_list(task_checks, check['check_id']):
                    task_checks.append(check)

            self.task_map[task_id] = task_checks

    def load_groups_from_xml(self, group_file):
        try:
            base = minidom.parse(group_file)
        except Exception, e:
            raise MappingError("An error occurred opening group file '%s': %s" % (group_file, e))

        # sometimes the data is all over the place
        for i in range(0, 2):
            for check_group_row in base.getElementsByTagName('Table1'):
                check_group_id = check_group_row.getElementsByTagName('CheckGroupID')[0].firstChild.data
                parent_check_node = check_group_row.getElementsByTagName('ParentCheckGroupID')
                if not parent_check_node:
                    continue

                parent_check_id = parent_check_node[0].firstChild.data

                if parent_check_id in self.appcheck_group and check_group_id not in self.appcheck_group:
                    self.appcheck_group.append(check_group_id)
                elif parent_check_id in self.thirdparty_group and check_group_id not in self.thirdparty_group:
                    self.thirdparty_group.append(check_group_id)

        self.thirdparty_group = sorted(self.thirdparty_group)
        self.appcheck_group = sorted(self.appcheck_group)

    def remap(self, unmapped_cwe_file_name):
        fp = open(unmapped_cwe_file_name, "w")

        self.task_map['186'].extend(self.thirdparty_checks)
        self.task_map['193'].extend([{'check_id': '*', 'check_name': 'Unmapped Check'}])

        keys = sorted(self.cwe_checks.iterkeys())
        for cwe in keys:
            if self.mapping.has_key(cwe):
                tasks = self.mapping[cwe]
                for task in tasks:
                    task_checks = []
                    if task in self.task_map.keys():
                        task_checks = self.task_map[task]

                    for check in self.cwe_checks[cwe]:

                        # If the check is assigned here already skip it
                        if self.check_mapped(self.task_map, check['check_id'], task):
                            continue

                        # If the check is assigned elsewhere do not put it in the catch-all task
                        if task == '193' and self.check_mapped(self.task_map, check['check_id'], task):
                            continue

                        task_checks.append(check)

                    self.task_map[task] = task_checks
            else:  # map to 193
                    fp.write("CWE-%s %d un-mapped\n" % (cwe, len(self.cwe_checks[cwe])))
                    task_mapping_found = False
                    task_checks = []
                    task = '193'
                    if task in self.task_map.keys():
                        task_checks = self.task_map[task]
                    for check in self.cwe_checks[cwe]:

                        # If the check is assigned elsewhere do not put it in the catch-all task
                        if self.check_mapped(self.task_map, check['check_id']):
                            continue

                        for chk in task_checks:
                            if chk['check_id'] == check['check_id']:
                                task_mapping_found = True
                        if not task_mapping_found:
                            task_checks.append(check)
                    self.task_map[task] = task_checks

        fp.close()

    def load_weaknesses_from_xml(self, weakness_file):
        try:
            base = minidom.parse(weakness_file)
        except Exception, e:
            raise MappingError("An error occured opening mapping file '%s': %s" % (weakness_file, e))

        cwe_checks = {}
        for weakness_row in base.getElementsByTagName('Table1'):
            check = {}
            check['check_id'] = weakness_row.getElementsByTagName('CheckID')[0].firstChild.data

            # Keep a running tally of the checks
            if not check['check_id'] in self.checks:
                self.checks.append(check['check_id'])

            check['check_group_id'] = weakness_row.getElementsByTagName('CheckGroupID')[0].firstChild.data
            check['check_name'] = weakness_row.getElementsByTagName('CheckName')[0].firstChild.data
            check['check_name'] = check['check_name'].replace('"', '&quot;')
            check['check_name'] = check['check_name'].replace('&', '&amp;')

            # try to map immediately based on check grouping, without CWE
            if self.check_mapped(self.task_map, check['check_id']):
                continue
            elif self.check_in_list(self.thirdparty_checks, check['check_id']):
                continue
            elif check['check_group_id'] in self.thirdparty_group:
                self.thirdparty_checks.append(check)
                continue

            cwe = weakness_row.getElementsByTagName('CWE')[0].firstChild.data
            check['cwe_desc'] = weakness_row.getElementsByTagName('CWE_Desc')[0].firstChild.data
            check['cwe_desc'] = check['cwe_desc'].replace('"', '&quot;')
            check['cwe_desc'] = check['cwe_desc'].replace('&', '&amp;')
            check['cwe_id'] = cwe[4:]

            weaknesses = []
            if cwe_checks.has_key(check['cwe_id']):
                weaknesses = cwe_checks[check['cwe_id']]
            weaknesses.append(check)
            cwe_checks[check['cwe_id']] = weaknesses

        self.cwe_checks = cwe_checks

    def output_mapping(self, file_name):
        fp = open(file_name, "w")
        keys = sorted(self.task_map.iterkeys())
        fp.write('<mapping weaknesses="%d">\n' % len(self.checks))
        for task_id in keys:
            task_checks = self.task_map[task_id]
            fp.write('\t<task id="%s" title="%s" confidence="%s">\n' % (
                task_id, self.base_tasks[task_id].attributes['title'].value, "low"))
            task_checks = sorted(task_checks, key=lambda x: x['check_name'])
            for weakness in task_checks:
                fp.write('\t\t<weakness type="check" id="%s" title="%s" />\n' % (weakness['check_id'],
                                                                                 weakness['check_name']))
            fp.write('\t</task>\n')
        fp.write('</mapping>\n')
        fp.close()

    def check_in_list(self, a_list, check_id):
        for item in a_list:
            if item['check_id'] == check_id:
                return True
        return False

    def check_mapped(self, task_map, check_id, selected_task=None):
        keys = task_map.iterkeys()

        if self.check_in_list(self.thirdparty_checks, check_id):
            return True

        for task_id in keys:
            if selected_task:
                if task_id != selected_task:
                    continue
            task_checks = task_map[task_id]
            if self.check_in_list(task_checks, check_id):
                return True

        return False

    def find_missing_checks(self):
        missing_checks = False
        for check_id in self.checks:
            if not self.check_mapped(self.task_map, check_id):
                print "*** Check %s is not mapped" % check_id
                missing_checks = True
        return missing_checks

def main(argv):

    usage = "Usage: %s <base mapping> <custom map> <webinspect groups> <webinspect checks> <unmapped cwes> <webinspect map> \n" % (argv[0])

    if len(argv) == 2 and argv[1] == 'help':
        print usage
        print "base mapping: (input) docs/base_cwe/sde_cwe_map.xml"
        print "custom map: (input) Task->WebInspect check mapping in xml format [i.e. custom_webinspect_map.xml]"
        print "webinspect groups: (input) WebInspect groups in xml format [i.e. webinspect_groups.xml]"
        print "webinspect checks: (input) WebInspect checks in xml format [i.e. webinspect_checks.xml]"
        print "unmapped cwes: (output) list of cwes that were not mapped using the mapping"
        print "webinspect map: (output) WebInspect map file"
        sys.exit(0)
    elif len(argv) < 7:
        print usage
        sys.exit(1)

    base = Mapping()

    print "Loading CWE map..."
    base.load_base_mapping_from_xml(argv[1])

    print "Loading custom map..."
    base.load_custom_mapping_from_xml(argv[2])

    print "Loading WebInspect Groups..."
    base.load_groups_from_xml(argv[3])

    print "Loading WebInspect Checks..."
    base.load_weaknesses_from_xml(argv[4])

    print "Re-mapping Checks... unmapped CWE's recorded in %s" % argv[5]
    base.remap(argv[5])

    print "Validating..."
    if base.find_missing_checks():
        print "Aborted"
        sys.exit(1)

    print "Outputting WebInspect map to %s..." % argv[6]
    base.output_mapping(argv[6])

    print "Done."        

if __name__ == "__main__":
    main(sys.argv)

