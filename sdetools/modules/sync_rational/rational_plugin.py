# Copyright SDElements Inc
# Extensible two way integration with Rational

import re
from datetime import datetime

from sdetools.extlib import http_req
from sdetools.extlib.defusedxml import minidom
from sdetools.sdelib.commons import urlencode_str
from sdetools.sdelib.restclient import RESTBase
from sdetools.sdelib.restclient import URLRequest, APIError
from sdetools.alm_integration.alm_plugin_base import AlmTask, AlmConnector
from sdetools.alm_integration.alm_plugin_base import AlmException

from sdetools.sdelib import log_mgr
logger = log_mgr.mods.add_mod(__name__)

RE_MAP_RANGE_KEY = re.compile('^\d+(-\d+)?$')
GITHUB_DEFAULT_PRIORITY_MAP = {
    '7-10': 'High',
    '4-6': 'Medium',
    '1-3': 'Low',
    }

OSLC_PREFIX = 'oslc'
PURL_PREFIX = 'dcterms'
RDF_PREFIX = 'rdf'


class RationalAPI(RESTBase):
    """ Base plugin for Rational """

    def __init__(self, config):
        base_path = config['rational_context_root']
        super(RationalAPI, self).__init__('alm', 'Rational', config, base_path)

    def get_custom_headers(self, target, method):
        return [('Accept', 'application/rdf+xml')]


class RationalTask(AlmTask):
    """ Representation of a task in Rational"""

    def __init__(self, task_id, alm_id, status, timestamp, done_statuses):
        self.task_id = task_id
        self.alm_id = alm_id
        self.status = status
        self.timestamp = timestamp
        self.done_statuses = done_statuses

    def get_task_id(self):
        return self.task_id

    def get_alm_id(self):
        return self.alm_id

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
        return datetime.strptime(self.timestamp, '%Y-%m-%dT%H:%M:%SZ')


class RationalConnector(AlmConnector):
    alm_name = 'Rational'
    ALM_NEW_STATUS = 'rational_new_status'
    ALM_DONE_STATUSES = 'rational_done_statuses'

    def __init__(self, config, alm_plugin):
        """ Initializes connection to Rational """
        super(RationalConnector, self).__init__(config, alm_plugin)

        config.add_custom_option(self.ALM_NEW_STATUS, 'Status to set for new'
                                 'tasks in Rational', default='open')
        config.add_custom_option(self.ALM_DONE_STATUSES, 'Statuses that '
                                 'signify a task is Done in Rational',
                                 default='closed')

    def initialize(self):
        super(RationalConnector, self).initialize()

        # Verify that the configuration options are set properly
        for item in [self.ALM_NEW_STATUS, self.ALM_DONE_STATUSES]:
            if not self.config[item]:
                raise AlmException('Missing %s in configuration' % item)

        self.config[self.ALM_DONE_STATUSES] = self.config[self.ALM_DONE_STATUSES].split(',')

    def process_rdf_url(self, url):
        """ Remove the base url so we can pass the new url into call api """
        return url.remove(self.baseUri, '')
        
    def alm_connect_server(self):
        """ Verifies that Rational connection works """
        # Check if user can successfully authenticate and retrieve service catalog
        try:
            # Get catalog
            rootServices = minidom.parse(self.alm_plugin.call_api('rootservices'))
            serviceProviderCatalogTag = rootServices.getElementsByTagName(self.get_OSLC_CM_id('cmServiceProviders'))
            serviceProviderCatalogURL = serviceProviderCatalogTag[0].attributes[self.get_RDF_id('resource')].value
            self.serviceCatalog = self.alm_plugin.call_api(process_rdf_url(serviceProviderCatalogURL))
        except APIError, err:
            raise AlmException('Unable to connect retrieve Rational service catalog (Check server URL, user, pass).'
                               'Reason: %s' %str(err))

        if not self.serviceCatalog:
            raise AlmException('Unable to connect retrieve Rational service catalog (Check server URL, user, pass).')

    def get_purl_id(self, name):
        return '%s:%s' % (PURL_PREFIX, name)

    def get_OSLC_id(self, name):
        return '%s:%s' % (OSLC_PREFIX, name)

    def get_OSLC_CM_id(self, name):
        return '%s_cm:%s' % (OSLC_PREFIX, name)

    def get_RDF_id(self, name):
        return '%s:%s' % (RDF_PREFIX, name)

    def alm_connect_project(self):
        """ Verifies that the Rational project exists """
        catalog = minidom.parse(self.serviceCatalog)
        project_name = self.config['alm_project']
        for service_provider in catalog.getElementsByTagName(self.get_purl_id('serviceProvider')):
            names = service_provider.getElementsByTagName(self.get_purl_id('title'))
            
            if names[0].childnodes[0].data == project_name:
                details = service_provider.getElementsByTagName(self.get_OSLC_id('details'))
                project_url = details[0].attributes[self.get_RDF_id('resource')].value

                try:
                    response = self.alm_plugin.call_api('%s' % project_url.replace(self.baseUri, ''))
                except APIError, err:
                    raise AlmException('Unable to find Rational project %s. Reason: %s' % (project_name, err))

                if not response:
                    raise AlmException('Unable to find Rational project %s' % project_name)

                # Store URL of list of available services
                self.project_services_url = service_provider.getElementsByTagName(self.get_OSLC_id('ServiceProvider'))
                self.project_services_url = self.project_services_url[0].attributes[self.get_RDF_id('about')].value

    def alm_get_task(self, task):
        pass

    def alm_add_task(self, task):
        pass

    def alm_update_task_status(self, task, status):
        pass

    def alm_disconnect(self):
        pass
