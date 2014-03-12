# Copyright SDElements Inc
# Extensible two way integration with Rational

import re
import urllib
import json
from datetime import datetime

from sdetools.sdelib.restclient import RESTBase
from sdetools.sdelib.restclient import URLRequest, APIError
from sdetools.alm_integration.alm_plugin_base import AlmTask, AlmConnector
from sdetools.alm_integration.alm_plugin_base import AlmException
from sdetools.extlib import markdown

from sdetools.sdelib import log_mgr
logger = log_mgr.mods.add_mod(__name__)

RE_MAP_RANGE_KEY = re.compile('^\d+(-\d+)?$')
MAX_CONTENT_SIZE = 30000
RATIONAL_DEFAULT_PRIORITY_MAP = {
    '7-10': 'High',
    '4-6': 'Medium',
    '1-3': 'Low',
}

RATIONAL_HTML_CONVERT = [
    (re.compile('<h[1-6]>'), '<br><strong>'),
    (re.compile('</h[1-6]>'), '</strong><br>'),
    ('<p>', ''),
    ('</p>', '<br><br>'),
    ('<pre><code>', '<span style="font-family: courier new,monospace;"><pre>'),
    ('</code></pre>', '</pre></span>'),
]

OSLC_CM_SERVICE_PROVIDER ='http://open-services.net/xmlns/cm/1.0/cmServiceProviders'
OSLC_CR_TYPE = "http://open-services.net/ns/cm#task"
AUTH_MSG = 'x-com-ibm-team-repository-web-auth-msg'
MSG_FAIL = 'authfailed'


class RationalAPI(RESTBase):
    """ Base plugin for Rational """

    def __init__(self, config):
        super(RationalAPI, self).__init__('alm', 'Rational', config)

    def parse_error(self, result):
        result = json.loads(result)

        error_msg = None
        if 'oslc:message' in result:
            error_msg = result['oslc:message']
        else:
            error_msg = result

        return error_msg

    def post_conf_init(self):
        self.base_path = self.config['rational_context_root']
        super(RationalAPI, self).post_conf_init()

    def call_api(self, target, method=URLRequest.GET, args=None, call_headers={}, auth_mode=None):
        call_headers['Accept'] = 'application/json'
        call_headers['OSLC-Core-Version'] = '2.0'

        try:
            return super(RationalAPI, self).call_api(target, method, args, call_headers, auth_mode)
        except Exception as e:
            raise AlmException('API Call failed. Target: %s ; Error: %s' % (target, e))


class RationalFormsLogin(RESTBase):
    """ Base plugin for Rational """

    def __init__(self, config):
        super(RationalFormsLogin, self).__init__('alm', 'Rational Forms Login', config)

    def post_conf_init(self):
        self.base_path = self.config['rational_context_root']
        super(RationalFormsLogin, self).post_conf_init()

    def encode_post_args(self, args):
        return urllib.urlencode(args)

    def parse_response(self, result, headers):
        for header, value in headers.items():
            if header == AUTH_MSG and value == MSG_FAIL:
                raise AlmException('Authentication failed: Check username or password')

        return result

    def call_api(self, target, method=URLRequest.GET, args=None, call_headers={}, auth_mode=None):
        if method == URLRequest.POST:
            call_headers['Content-Type'] = 'application/x-www-form-urlencoded'

        for cookie in self.cookiejar:
            if cookie.name == 'JSESSIONID':
                call_headers[cookie.name] = cookie.value

        try:
            result = super(RationalFormsLogin, self).call_api(target, method, args, call_headers, auth_mode)
        except Exception as e:
            raise AlmException('API Call failed. Target: %s ; Error: %s' % (target, e))

        return result


class RationalTask(AlmTask):
    """ Representation of a task in Rational"""

    def __init__(self, task_id, alm_url, alm_id, status, timestamp, done_statuses):
        self.task_id = task_id
        self.alm_url = alm_url
        self.alm_id = alm_id
        self.status = status
        self.timestamp = timestamp
        self.done_statuses = done_statuses

    def get_task_id(self):
        return self.task_id

    def get_alm_id(self):
        return self.alm_id

    def get_alm_url(self):
        return self.alm_url

    def get_priority(self):
        return self.priority

    def get_status(self):
        """ Translates Rational status into SDE status """
        if self.status in self.done_statuses:
            return 'DONE'
        else:
            return 'TODO'

    def get_timestamp(self):
        """ Returns a datetime object """
        return datetime.strptime(self.timestamp[:-5]+'Z', '%Y-%m-%dT%H:%M:%SZ')


class RationalConnector(AlmConnector):

    alm_name = 'Rational'
    cm_service_provider = None
    resource_url = None
    priorities = None
    ALM_DONE_STATUSES = 'rational_done_statuses'
    ALM_PRIORITY_MAP = 'alm_priority_map'

    def __init__(self, config, alm_plugin):
        """ Initializes connection to Rational """
        super(RationalConnector, self).__init__(config, alm_plugin)

        config.opts.add(self.ALM_DONE_STATUSES, 'Statuses that '
                                 'signify a task is Done in Rational',
                                 default='Completed,Done')
        config.opts.add(self.ALM_PRIORITY_MAP, 'Customized map from priority in SDE to Rational '
                                 '(JSON encoded dictionary of strings)', default='')
        config.opts.add('rational_context_root', 'Application context root: the part of the URL that accesses '
                                 'each application and Jazz Team Server', default='')
        config.opts.add('alm_issue_label', 'Tags applied to tasks in Rational (space separated)', default='SD-Elements')

    def initialize(self):
        super(RationalConnector, self).initialize()

        self.COOKIE_JSESSIONID = None
        self.mark_down_converter = markdown.Markdown(safe_mode="escape")

        for item in [self.ALM_DONE_STATUSES, 'rational_context_root', 'alm_issue_label']:

            if not self.config[item]:
                raise AlmException('Missing %s in configuration' % item)

        self.config[self.ALM_DONE_STATUSES] = self.config[self.ALM_DONE_STATUSES].split(',')

        if self.config['conflict_policy'] != 'alm':
            raise AlmException('Expected "alm" for configuration conflict_policy but got "%s". '
                               'Currently only Rational can be setup as authoritative server' % self.config['conflict_policy'])
        self.config.process_json_str_dict(self.ALM_PRIORITY_MAP)

        if not self.config[self.ALM_PRIORITY_MAP]:
            self.config[self.ALM_PRIORITY_MAP] = RATIONAL_DEFAULT_PRIORITY_MAP

        for key in self.config[self.ALM_PRIORITY_MAP]:
            if not RE_MAP_RANGE_KEY.match(key):
                raise AlmException('Unable to process %s (not a JSON dictionary). Reason: Invalid range key %s'
                                   % (self.ALM_PRIORITY_MAP, key))

    def _rational_forms_login(self, forms_client):
        forms_credentials = {
            'j_username': self.config['alm_user'],
            'j_password': self.config['alm_pass']
        }

        #Check to make sure that we can login
        try:
            forms_client.call_api('authenticated/j_security_check', args=forms_credentials, method=URLRequest.POST)
        except APIError, err:
            raise AlmException('Unable to connect to Rational (Check server URL, '
                               'user, pass). Reason: %s' % str(err))

        for cookie in forms_client.cookiejar:
            if cookie.name == 'JSESSIONID':
                self.COOKIE_JSESSIONID = cookie.value

    def alm_connect_server(self):
        """Check if user can successfully authenticate and retrieve service catalog"""


        forms_client = RationalFormsLogin(self.config)
        forms_client.set_auth_mode('cookie')

        try:
            forms_client.call_api(target='authenticated/identity')
        except APIError, err:
            raise AlmException('Unable to connect to Rational (Check server URL, '
                               'user, pass). Reason: %s' % str(err))

        auth = 'Basic'

        for cookie in forms_client.cookiejar:
            if cookie.name == 'JazzFormAuth' and cookie.value == 'Form':
                auth = 'Form'

        if auth == 'Form':
            self.alm_plugin.set_auth_mode('cookie')
            self._rational_forms_login(forms_client)

            if not self.COOKIE_JSESSIONID:
                raise AlmException('Unable to connect to Rational (Check server URL, user, pass)')
        else:
            self.alm_plugin.set_auth_mode('basic')

        try:
            catalog = self._call_api('rootservices')
        except APIError, err:
            raise AlmException('Unable to connect retrieve root services (Check server URL, user, pass). '
                               'Reason: %s' % str(err))

        root_services = catalog[self.alm_plugin.base_uri + '/rootservices']
        
        if OSLC_CM_SERVICE_PROVIDER not in root_services:
            raise AlmException('Change management service provider not found (Check server URL, user, pass)')
                               
        cm_service_providers = root_services[OSLC_CM_SERVICE_PROVIDER]
        # There should be only one service provider. It is still stored in a list, so using the first item.
        self.cm_service_provider = cm_service_providers[0]['value']
        
        self.cm_service_provider_target = self.cm_service_provider.replace(self.alm_plugin.base_uri + '/', '')

        try:
            self.service_catalog = self._call_api(self.cm_service_provider_target)
        except APIError, err:
            raise AlmException('Unable to connect retrieve service catalog'
                               '(Check server URL, user, pass). Reason: %s' % str(err))
                               
        if not self.service_catalog:
            raise AlmException('Unable to connect retrieve service catalog (Check connection settings).')

    def _call_api(self, target, args=None, method=URLRequest.GET):
        headers = {}

        if self.COOKIE_JSESSIONID:
            headers = {'Cookie': 'JSESSIONID=%s' % self.COOKIE_JSESSIONID}

        return self.alm_plugin.call_api(target, method=method, args=args, call_headers=headers)

    def _rational_get_priorities(self):
        try:
            resource_shapes = self._call_api(self.resource_shape_url)
        except APIError, err:
            logger.error(err)
            raise AlmException('Unable to get resource shapes from Rational')

        priorities = []
        for rs in resource_shapes['oslc:property']:
            if rs['oslc:name'] == 'priority':
                for p in rs['oslc:allowedValues']['oslc:allowedValue']:
                    priorities.append(self._rational_get_priority_details(p['rdf:resource']))

        return priorities

    def _rational_get_priority_details(self, priority_resource_url):
        priority_resource_url = priority_resource_url.replace(self.alm_plugin.base_uri+'/', '')

        try:
            priority_details = self._call_api(priority_resource_url)
        except APIError, err:
            logger.error(err)
            raise AlmException('Unable to get priority details from Rational. Url: %s' % priority_resource_url)

        return priority_details

    def _get_priority_literal(self, priority_name):
        for priority in self.priorities:
            if priority['dcterms:title'] == priority_name:
                return priority['rdf:about']
        return None

    def alm_connect_project(self):
        for service_provider in self.service_catalog['oslc:serviceProvider']:
            if service_provider['dcterms:title'] == self.config['alm_project']:
                self.resource_url = service_provider['rdf:about']

        if not self.resource_url:
            raise AlmException('Unable to retrieve resource url for project "%s" (Check project name).' %
                               self.config['alm_project'])

        self.cm_resource_service = self.resource_url.replace(self.alm_plugin.base_uri+'/', '')
        self.services = self._call_api(self.cm_resource_service)

        query_url = self.services['oslc:service'][1]['oslc:queryCapability'][0]['oslc:queryBase']['rdf:resource']

        self.query_url = query_url.replace(self.alm_plugin.base_uri + '/', '')
        # Search the services for the proper creation factory and retrieve the creation and resource shape urls
        try:
           for service in self.services['oslc:service']:
                if 'oslc:creationFactory' in service:
                    for factory in service['oslc:creationFactory']:
                        if 'oslc:usage' in factory:
                            for resource in factory['oslc:usage']:
                                if resource['rdf:resource'] == OSLC_CR_TYPE:
                                    creation_url = factory['oslc:creation']['rdf:resource']
                                    resource_shape_url = factory['oslc:resourceShape']['rdf:resource']
                                    self.creation_url = creation_url.replace(self.alm_plugin.base_uri+'/', '')
                                    self.resource_shape_url = resource_shape_url.replace(self.alm_plugin.base_uri+'/', '')
        except KeyError as e:
            raise AlmException('Unable to retrieve creation url or resource shape. Error msg: %s' % e)

        self.priorities = self._rational_get_priorities()

    def alm_validate_configurations(self):
        pass

    def _extract_task_id(self, full_task_id):
        task_id = None
        task_search = re.search('^(\d+)-([^\d]+\d+)$', full_task_id)
        if task_search:
            task_id = task_search.group(2)
        return task_id

    def alm_get_task(self, task):
        """Returns a RationalTask object that has the same ID as the given task"""

        task_id = self._extract_task_id(task['id'])
        if not task_id:
            return None

        try:
            # Fields parameter will filter response data to only contain story status, name, timestamp and id
            work_items = self._call_api('%s/workitems?oslc.where=dcterms:title="%s:*"' %
                                                  (self.query_url, task_id))
        except APIError, err:
            logger.error(err)
            raise AlmException('Unable to get task %s from Rational' % task_id)

        if work_items['oslc:responseInfo']['oslc:totalCount'] == 0:
            return None

        work_item_url = work_items['oslc:results'][0]['rdf:resource']
        work_item_target = work_item_url.replace(self.alm_plugin.base_uri+'/', '')
        try:
            work_item = self._call_api(work_item_target)
        except APIError, err:
            logger.error(err)
            raise AlmException('Unable to get task %s from Rational' % task_id)

        logger.info('Found task: %s', task_id)
        return RationalTask(task_id,
                                  work_item_url,
                                  work_item['dcterms:identifier'],
                                  work_item['oslc_cm:status'],
                                  work_item['dcterms:modified'],
                                  self.config[self.ALM_DONE_STATUSES])

    def alm_add_task(self, task):
        """Adds a task with the specified status if provided, otherwise status is set to new"""

        priority_name = self.translate_priority(task['priority'])
        priority_literal_resource = self._get_priority_literal(priority_name)

        create_args = {
            'dcterms:title': task['title'],
            'dcterms:description': self.sde_get_task_content(task),
            'oslc_cmx:priority': priority_literal_resource,
            'dcterms:subject': self.config['alm_issue_label'],
        }

        if (self.config['alm_standard_workflow'] and
                (task['status'] == 'DONE' or task['status'] == 'NA')):
            create_args['oslc_cm:status'] = self.config[self.ALM_DONE_STATUSES][0]

        try:
            self._call_api(self.creation_url,
                           method=self.alm_plugin.URLRequest.POST,
                           args=create_args)
            logger.debug('Task %s added to Rational Project', task['id'])
        except APIError, err:
            raise AlmException('Unable to add task %s to Rational because of %s'
                               % (task['id'], err))

        alm_task = self.alm_get_task(task)

        return 'Project: %s; Task: %s; URL: %s' % (
               self.config['alm_project'], alm_task.get_alm_id(), alm_task.get_alm_url()
        )

    def alm_update_task_status(self, task, status):
        pass

    def alm_disconnect(self):
        pass

    def convert_markdown_to_alm(self, content, ref):
        s = self.mark_down_converter.convert(content)

        # We do some jumping through hoops to add <br> at end of each
        # line for segments between code tags
        sliced = s.split('<code>')
        s = [sliced[0]]
        for item in sliced[1:]:
            item = item.split('</code>')
            item[0] = item[0].replace('\n', '<br>\n')
            s.append('</code>'.join(item))
        s = '<code>'.join(s)

        for before, after in RATIONAL_HTML_CONVERT:
            if type(before) is str:
                s = s.replace(before, after)
            else:
                s = before.sub(after, s)

        if len(s) > MAX_CONTENT_SIZE:
            logger.warning('Content too long for %s - Truncating.' % ref)
            s = s[:MAX_CONTENT_SIZE]

        return s

    def translate_priority(self, priority):
        pmap = self.config[self.ALM_PRIORITY_MAP]

        if not pmap:
            return None

        try:
            priority = int(priority)
        except TypeError:
            logger.error('Could not coerce %s into an integer' % priority)
            raise AlmException("Error in translating SDE priority to Rational priority: "
                               "%s is not an integer priority" % priority)

        for key in pmap:
            if '-' in key:
                lrange, hrange = key.split('-')
                lrange = int(lrange)
                hrange = int(hrange)
                if lrange <= priority <= hrange:
                    return pmap[key]
            else:
                if int(key) == priority:
                    return pmap[key]
