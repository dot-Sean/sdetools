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
RATIONAL_DEFAULT_PRIORITY_MAP = {
    '7-10': 'High',
    '4-6': 'Medium',
    '1-3': 'Low',
    }

OSLC_CM_SERVICE_PROVIDER ='http://open-services.net/xmlns/cm/1.0/cmServiceProviders'
OSLC_CR_TYPE = "http://open-services.net/ns/cm#task"


class RationalAPI(RESTBase):
    """ Base plugin for Rational """

    def __init__(self, config):
        super(RationalAPI, self).__init__('alm', 'Rational', config)

    def parse_response(self, result, headers):
        return (result, headers)

    def post_conf_init(self):
        self.base_path = self.config['rational_context_root']
        super(RationalAPI, self).post_conf_init()

    def call_api(self, target, method=URLRequest.GET, args=None, call_headers={}, auth_mode=None, show_headers=False):
        call_headers['Accept'] = 'application/json'
        call_headers['OSLC-Core-Version'] = '2.0'

        try:
            result = super(RationalAPI, self).call_api(target, method, args, call_headers, auth_mode)
        except Exception as e:
            raise AlmException('API Call failed. Target: %s ; Error: %s' % (target, e))
        if show_headers:
            return result
        else:
            return json.loads(result[0])


class RationalFormsLogin(RESTBase):
    """ Base plugin for Rational """

    def __init__(self, config):
        super(RationalFormsLogin, self).__init__('alm', 'Rational Forms Login', config)

    def post_conf_init(self):
        self.base_path = self.config['rational_context_root']
        super(RationalFormsLogin, self).post_conf_init()

    def encode_post_args(self, args):
        return urllib.urlencode(args)

    def parse_response(self, result, headers, show_headers=False):
        return (result, headers)

    def call_api(self, target, method=URLRequest.GET, args=None, call_headers={}, auth_mode=None):

        if method == URLRequest.POST:
            call_headers['Content-Type'] = 'application/x-www-form-urlencoded'

        for cookie in self.cookiejar:
            if cookie.name == 'JSESSIONID':
                call_headers[cookie.name] = cookie.value
            elif cookie.name == 'JSESSIONIDSSO':
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
    ALM_NEW_STATUS = 'rational_new_status'
    ALM_DONE_STATUSES = 'rational_done_statuses'
    ALM_PRIORITY_MAP = 'alm_priority_map'

    def __init__(self, config, alm_plugin):
        """ Initializes connection to Rational """
        super(RationalConnector, self).__init__(config, alm_plugin)

        config.opts.add(self.ALM_NEW_STATUS, 'Status to set for new '
                                 'tasks in Rational', default='New')
        config.opts.add(self.ALM_DONE_STATUSES, 'Statuses that '
                                 'signify a task is Done in Rational',
                                 default='Completed,Done')
        config.opts.add(self.ALM_PRIORITY_MAP, 'Customized map from priority in SDE to RTC '
                                 '(JSON encoded dictionary of strings)', default='')
        config.opts.add('rational_context_root', 'Application context root: the part of the URL that accesses '
                                 'each application and Jazz Team Server', default='')

    def initialize(self):
        super(RationalConnector, self).initialize()

        self.COOKIE_JSESSIONID = None
        self.mark_down_converter = markdown.Markdown(safe_mode="escape")

        # Verify that the configuration options are set properly
        for item in [self.ALM_NEW_STATUS, self.ALM_DONE_STATUSES]:
            if not self.config[item]:
                raise AlmException('Missing %s in configuration' % item)

        self.config[self.ALM_DONE_STATUSES] = self.config[self.ALM_DONE_STATUSES].split(',')

        if self.config['conflict_policy'] != 'alm':
            raise AlmException('Expected "alm" for configuration conflict_policy but got "%s". '
                               'Currently only Rational Team Concert can be setup as authoritative server' % self.config['conflict_policy'])
        self.config.process_json_str_dict(self.ALM_PRIORITY_MAP)

        if not self.config[self.ALM_PRIORITY_MAP]:
            self.config[self.ALM_PRIORITY_MAP] = RATIONAL_DEFAULT_PRIORITY_MAP

        for key in self.config[self.ALM_PRIORITY_MAP]:
            if not RE_MAP_RANGE_KEY.match(key):
                raise AlmException('Unable to process %s (not a JSON dictionary). Reason: Invalid range key %s'
                                   % (self.ALM_PRIORITY_MAP, key))

    def _rtc_forms_login(self):

        forms_credentials = {
            'j_username': self.config['alm_user'],
            'j_password': self.config['alm_pass']
        }

        login_client = RationalFormsLogin(self.config)
        login_client.set_auth_mode('cookie')

        #RTC does not allow direct login - get a cookie first
        try:
            login_client.call_api('authenticated/identity')
        except APIError, err:
            raise AlmException('Unable to connect to RTC (Check server URL, '
                               'user, pass). Reason: %s' % str(err))

        #Check to make sure that we can login
        try:
            login_client.call_api('authenticated/j_security_check', args=forms_credentials, method=URLRequest.POST)
        except APIError, err:
            raise AlmException('Unable to connect to RTC (Check server URL, '
                               'user, pass). Reason: %s' % str(err))

        for cookie in login_client.cookiejar:
            if cookie.name == 'JSESSIONID':
                self.COOKIE_JSESSIONID = cookie.value

    def alm_connect_server(self):
        """Check if user can successfully authenticate and retrieve service catalog"""

        try:
            cookie = self.alm_plugin.call_api('authenticated/identity', show_headers=True)[1]['set-cookie']
        except APIError, err:
            raise AlmException('Unable to connect to RTC (Check server URL, '
                               'user, pass). Reason: %s' % str(err))
        auth = cookie[cookie.find('JazzFormAuth=')+len('JazzFormAuth='):cookie.find('JazzFormAuth=')+len('JazzFormAuth=')+4]

        if auth == 'Form':
            # We will authenticate via cookie
            self.alm_plugin.set_auth_mode('cookie')

            self._rtc_forms_login()

            if not self.COOKIE_JSESSIONID:
                raise AlmException('Unable to connect to HP Alm service (Check server URL, user, pass)')
        else:
            pass

        try:
            catalog = self.alm_plugin.call_api('rootservices')
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
            raise AlmException('Unable to connect retrieve Rational service catalog (Check server URL, user, pass). '
                               'Reason: %s' % str(err))
                               
        if not self.service_catalog:
            raise AlmException('Unable to connect retrieve service catalog (Check connection settings).')

    def _call_api(self, target, args=None, method=URLRequest.GET):

        headers = {}

        if self.COOKIE_JSESSIONID:
            headers = {'Cookie': 'JSESSIONID=%s' % self.COOKIE_JSESSIONID}

        return self.alm_plugin.call_api(target, method=method, args=args, call_headers=headers)

    def _rtc_get_priorities(self):

        try:
            resource_shapes = self._call_api(self.resource_shape_url)
        except APIError, err:
            logger.error(err)
            raise AlmException('Unable to get resource shapes from Rational')

        priorities = []
        for rs in resource_shapes['oslc:property']:
            if rs['oslc:name'] == 'priority':
                for p in rs['oslc:allowedValues']['oslc:allowedValue']:
                    priorities.append(self._rtc_get_priority_details(p['rdf:resource']))

        return priorities

    def _rtc_get_priority_details(self, priority_resource_url):

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

        self.priorities = self._rtc_get_priorities()

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
        }

        if (self.config['alm_standard_workflow'] and
                (task['status'] == 'DONE' or task['status'] == 'NA')):
            create_args['oslc_cm:status'] = self.config[self.ALM_DONE_STATUSES][0]

        try:
            self._call_api(self.creation_url,
                           method=self.alm_plugin.URLRequest.POST,
                           args=create_args)
            #print work_item
            logger.debug('Task %s added to Rational Project', task['id'])
        except APIError, err:
            raise AlmException('Unable to add task %s to Rational because of %s'
                               % (task['id'], err))

        alm_task = self.alm_get_task(task)

        return 'Project: %s, Task: %s' % (self.config['alm_project'], alm_task.get_alm_id())

    def alm_update_task_status(self, task, status):
        pass

    def alm_disconnect(self):
        pass

    def convert_markdown_to_alm(self, content, ref):
        return self.mark_down_converter.convert(content)

    def translate_priority(self, priority):
        """ Translates an SDE priority into a GitHub label """
        pmap = self.config[self.ALM_PRIORITY_MAP]

        if not pmap:
            return None

        try:
            priority = int(priority)
        except TypeError:
            logger.error('Could not coerce %s into an integer' % priority)
            raise AlmException("Error in translating SDE priority to Rational label: "
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
