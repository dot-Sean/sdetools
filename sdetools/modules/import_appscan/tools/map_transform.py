#!/usr/bin/python
import sys
import os
from xml.sax.saxutils import escape, quoteattr

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from xml.dom import minidom


class MappingError(Exception):
    pass


class Mapping:
    def __init__(self):
        self.check_causes = {}
        self.task_cause_map = {'186': ['insecureThirdPartySoftware',
                                       'missingPatchesForThirdPartyProds','vulnActiveX','vulnSOAPserializer'],
                            '49': ['sampleScriptsFound', 'backDoorLeftBehind', 'debugInfoInHtmlSource'],
                            '23': ['nonHttpOnlySessionCookie'],
                            '33': ['hiddenParameterUsed'],
                            '42': ['remoteFileInclusion'],
                            '203': ['formatStringsVulnerability'],
                            '47': ['errorMessagesReturned'],
                            '50': ['dotDotNotSanitized'],
                            '21': ['sensitiveDataNotSSL'],
                            '11': ['redirectionFromWithinSite'],
                            '22': ['nonSecureCookiesSentOverSSL'],
                            '60': ['WB_InsecureCryptoStorage'],
                            '38': [],
                            '196':['WB_TaintPropHazardousAPI'],
                            '64': ['SensitiveCache'],
                            '40': ['XPath Injection'],
                            '193': ['tempFilesLeftBehind'],
                            '219': ['GETParamOverSSL']
                            }
        self.mapping = {}
        self.third_party_checks = []
        self.category_checks = {}
        self.base_tasks = {}
        self.checks = []
        self.task_map = {}
        self.task_map['186'] = []
        self.task_map['193'] = [{'check_id': '*', 'cause_id': '','category_id': '', 'check_name': 'Unmapped Check'}]

    def load_causes_from_xml(self, third_party_map):
        try:
            base = minidom.parse(third_party_map)
        except Exception, e:
            raise MappingError("An error occurred opening mapping file '%s': %s" % (third_party_map, e))

        check_causes = {}
        for check_row in base.getElementsByTagName('ROW'):
            causes = []
            issue_type_id = check_row.attributes['ISSUETYPEID'].value
            if issue_type_id in check_causes:
                causes = check_causes[issue_type_id]
            causes.append(check_row.attributes['CAUSEID'].value)
            check_causes[issue_type_id] = causes
        self.check_causes = check_causes

    def load_base_mapping_from_xml(self, mapping_file):
        try:
            base = minidom.parse(mapping_file)
        except Exception, e:
            raise MappingError("An error occured opening mapping file '%s': %s" % (mapping_file, e))

        category_mapping = {}
        for task in base.getElementsByTagName('task'):
            self.base_tasks[task.attributes['id'].value] = task
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
                check['cause_id'] = check_row.attributes['cause'].value
                check['check_name'] = check_row.attributes['title'].value
                debug = 'GD_CreditCardDinersClub' == check['check_id'] and False
                if debug:
                    print "Adding %s to T%s" % (check['check_id'], task_id)
                task_checks.append(check)

            self.task_map[task_id] = task_checks

    def load_weaknesses_from_xml(self, checks_file):
        try:
            base = minidom.parse(checks_file)
        except Exception, e:
            raise MappingError("An error occurred opening checks file '%s': %s" % (checks_file, e))

        # Map to tasks if possible
        for check_row in base.getElementsByTagName('ROW'):
            check = {}
            check['check_id'] = check_row.attributes['ID'].value
            check['cwe_id'] = check_row.attributes['CWEID'].value
            check['cause_id'] = check_row.attributes['CAUSEID'].value
            check['check_name'] = check_row.attributes['STRING'].value

            if check['check_name'].find('#') > 0:
                check['check_name'] = check['check_name'][(check['check_name'].index("#")+2):]

            if self.check_mapped(self.task_map, check['check_id']):
                continue

            debug = 'GD_CreditCardDinersClub' == check['check_id'] and False
            added = False
            task_id = self.get_task_based_cause(check['cause_id'])
            if task_id:
                if debug:
                    print "Cause %s maps to task %s" % (check['cause_id'], task_id)
                if not self.task_map.has_key(task_id):
                    self.task_map[task_id] = []
                if not self.check_in_list(self.task_map[task_id], check['check_id']):
                    self.task_map[task_id].append(check)
                    added = True
                    if debug:
                        print ">> added to %s " % task_id

        # Try to map to 193
        for check_row in base.getElementsByTagName('ROW'):
            check = {}
            check['check_id'] = check_row.attributes['ID'].value
            check['cwe_id'] = check_row.attributes['CWEID'].value
            check['cause_id'] = check_row.attributes['CAUSEID'].value
            check['check_name'] = check_row.attributes['STRING'].value

            if not self.check_mapped(self.task_map, check['check_id']) and \
                    not self.check_in_list(self.task_map['193'], check['check_id']):
                self.task_map['193'].append(check)
                if debug:
                    print "added to 193"

    def get_task_based_cause(self, check_cause):
        for task_id in self.task_cause_map.keys():
            for task_cause in self.task_cause_map[task_id]:
                if task_cause == check_cause:
                    return task_id
        return None

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
            fp.write('\t<task id="%s" title="%s" confidence="%s">\n' %
                     (task_id, self.base_tasks[task_id].attributes['title'].value, confidence))
            task_checks = sorted(task_checks)
            for check in task_checks:
                fp.write('\t\t<weakness type="check" id="%s" cause="%s" title=%s />\n' % (
                    check['check_id'], check['cause_id'], quoteattr(escape(check['check_name']))))
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
    usage = "Usage: %s <check causes> <custom map> <appscan checks> <appscan map>\n" % (argv[0])

    if len(argv) == 2 and argv[1] == 'help':
        print usage
        print "check causes: (input) list of checks/causes (i.e. issuetypecauses.xml)"
        print "custom map: (input) Task->WebInspect check mapping in xml format [i.e. custom_webinspect_map.xml]"
        print "appscan checks: (input) AppScan checks in xml format [i.e. appscan_checks.xml]"
        print "appscan map: (output) AppScan map file"
        sys.exit(0)
    elif len(argv) < 5:
        print usage
        sys.exit(1)

    base = Mapping()

    print "Loading third party map..."
    base.load_causes_from_xml(argv[1])

    print "Loading custom map..."
    base.load_custom_mapping_from_xml(argv[2])

    print "Loading AppScan Checks..."
    base.load_weaknesses_from_xml(argv[3])

    print "Validating..."
    if base.find_missing_checks():
        print "Aborted"
        sys.exit(1)

    print "Outputting AppScan map to %s..." % argv[4]
    base.output_mapping(argv[4])

    print "Done."


if __name__ == "__main__":
    main(sys.argv)

