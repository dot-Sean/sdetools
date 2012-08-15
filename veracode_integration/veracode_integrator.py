#!/usr/bin/python
import sys
from base_integrator import BaseIntegrator, IntegrationError
from sdelib.conf_mgr import config
from xml.dom import minidom

REQUIRED_ATTRIBS = ['issueid', 'cweid', 'categoryid', 'categoryname', 'description', 'severity', 'module']
LOCATION_ATTRIBS = ['sourcefilepath', 'sourcefile', 'line', 'location']
SOURCE_ID = "VC"

__all__ = ['VeracodeIntegrator']

def args_validator(config, args):
    """
    Validator helper for argument parsing. Returns error description in case of error,
    or None if validate passed.
    """
    if not args:
        return "Missing commit argument"
    if args[0] <> 'true' and args[0] != 'false':
        return "Invalid value for commit '%s'. Specify 'true' or 'false'" % (args[0])

    return None

class VeracodeIntegrationError(IntegrationError):
    pass

class VeracodeIntegrator(BaseIntegrator):

    def __init__(self, config):
        BaseIntegrator.__init__(self, config)
        self.raw_findings = []

    def _init_config(self):
        BaseIntegrator._init_config(self)
        self.config.add_custom_option("report_xml", "Veracode Report XML", "x")
        self.config.set_custom_args(
            'commit',
            'commit (true|false)',
            "'true'=commit new tasks or 'false'=test run only",
            args_validator)

    def parse(self):
        try:
            base = minidom.parse(config['report_xml'])
        except KeyError, ke:
            raise VeracodeIntegrationError("Missing configuration option 'report_xml'")
        except Exception, e:
            raise VeracodeIntegrationError("Error opening report xml (%s)" % config['report_xml'])

        detailed_reports = base.getElementsByTagName('detailedreport')
        if len(detailed_reports) != 1:
            raise VeracodeIntegrationError('An unexpected number of detailedreport nodes found (%d)' % (len(detailed_reports)))
        dr = detailed_reports[0]
        self.report_id = "%s-%s (%s-b%s) %s" % (SOURCE_ID,dr.attributes['app_name'].value,dr.attributes['app_id'].value,dr.attributes['build_id'].value,dr.attributes['generation_date'].value)

        for node in base.getElementsByTagName('flaw'):
            entry = {}
            for attr in REQUIRED_ATTRIBS:
                if attr not in node.attributes.keys():
                    raise VeracodeIntegrationError('Required attribute %s missing' % (attr))
                else:
                    entry[attr] = node.attributes[attr].value
            for attr in LOCATION_ATTRIBS:
                if attr in  node.attributes.keys():
                    entry[attr] = node.attributes[attr].value

            self.raw_findings.append(entry)

    def output_raw_findings(self):
        for item in self.raw_findings:
            print '%5s,%5s,%5s' % (item['issueid'], item['cweid'], item['categoryid'])
            print item['description'][:120]

    def get_raw_findings(self):
        return self.raw_findings

    def generate_findings(self):
        self.findings[:] = []
        for item in self.get_raw_findings():
            finding = {}
            finding['cweid'] = item['cweid']
            finding['description'] = item['description']
            if(item.has_key('sourcefilepath')):
                finding['source'] = item['sourcefilepath']
            if(item.has_key('line')):
                finding['line'] = item['line']
            if(item.has_key('inputvector')):
                finding['source'] = item['inputvector']
            self.findings.append( finding )

def main(argv):
    vc_integrator = VeracodeIntegrator(config)

    try:
        vc_integrator.parse_args(argv)
    except:
        sys.exit(1)

    vc_integrator.load_mapping_from_xml()
    vc_integrator.parse()

    commit = (config['commit'] == 'true')
    vc_integrator.import_findings(commit)

if __name__ == "__main__":
    main(sys.argv)

