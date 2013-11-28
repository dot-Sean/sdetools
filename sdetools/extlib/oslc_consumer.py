# Copyright SDElements Inc
# Extensible two way integration with OSLC

import json
from sdetools.sdelib.restclient import RESTBase
from sdetools.sdelib.restclient import URLRequest, APIError
from sdetools.alm_integration.alm_plugin_base import AlmTask, AlmConnector
from sdetools.alm_integration.alm_plugin_base import AlmException


class OSLCAPI(RESTBase):

    """ Base plugin for OSLC Consumer """

    def __init__(self, config):
        super(OSLCAPI, self).__init__('alm', 'OSLC', config)

    def post_conf_init(self):
        super(OSLCAPI, self).post_conf_init()

    def call_api(self, target, method=URLRequest.GET, args=None):

        headers = {'Accept': 'application/json', 'OSLC-Core-Version': '2.0'}
        return super(OSLCAPI, self).call_api(target, method, args, headers)


class OSLCConnector(AlmConnector):

    OSLC_SERVICE_PROVIDER = None
    OSLC_APP_NAME = None
    OSLC_TYPE = None
    ALM_PRIORITY_MAP = 'alm_priority_map'
    service_provider_uri = None

    def __init__(self, config, alm_plugin):
        """ Initializes connection to OSLC """
        super(OSLCConnector, self).__init__(config, alm_plugin)
        config.add_custom_option(self.ALM_PRIORITY_MAP, ('Customized map from priority in SDE to %s '
                                 '(JSON encoded dictionary of strings)' % self.OSLC_APP_NAME), default='')

    def alm_connect_server(self):

        try:
            catalog = self.alm_plugin.call_api('rootservices')
        except APIError, err:
            raise AlmException('Unable to connect retrieve root services (Check server URL, user, pass).'
                               'Reason: %s' % str(err))

        root_services = catalog[self.alm_plugin.base_uri + '/rootservices']

        if self.OSLC_SERVICE_PROVIDER not in root_services:
            raise AlmException('Service provider not found (Check server URL, user, pass).')

        service_providers = root_services[self.OSLC_SERVICE_PROVIDER]
        self.service_provider_uri = service_providers[0]['value']

        service_provider_target = self.service_provider_uri.replace(self.alm_plugin.base_uri+'/', '')

        try:
            service_catalog = self.alm_plugin.call_api(service_provider_target)
        except APIError, err:
            raise AlmException('Unable to connect retrieve service catalog (Check server URL, user, pass).'
                               'Reason: %s' % str(err))

        if not service_catalog:
            raise AlmException('Unable to connect retrieve service catalog (Check server URL, user, pass).')

        resource_url = None
        for service_provider in service_catalog['oslc:serviceProvider']:
            if service_provider['dcterms:title'] == self.config['alm_project']:
                resource_url = service_provider['rdf:about']

        if not resource_url:
            raise AlmException('Unable to connect retrieve resource url (Check server URL, user, pass).')

        resource_service = resource_url.replace(self.alm_plugin.base_uri+'/', '')
        services = self.alm_plugin.call_api(resource_service)
        #print json.dumps(services['oslc:service'][1], indent=4)

        for service in services['oslc:service']:
            if 'oslc:queryCapability' in service:
                query_url = service['oslc:queryCapability'][0]['oslc:queryBase']['rdf:resource']
                self.query_url = query_url.replace(self.alm_plugin.base_uri+'/', '')
            if 'oslc:creationFactory' in service:
                for factory in service['oslc:creationFactory']:
                    if 'oslc:usage' in factory:
                        #print json.dumps( factory, indent=4)
                        for resource in factory['oslc:usage']:
                            if resource['rdf:resource'] == self.OSLC_TYPE:
                                creation_url = factory['oslc:creation']['rdf:resource']
                                resource_shape_url = factory['oslc:resourceShape']['rdf:resource']
                                self.creation_url = creation_url.replace(self.alm_plugin.base_uri+'/', '')
                                self.resource_shape_url = resource_shape_url.replace(self.alm_plugin.base_uri+'/', '')

        self.priorities = self._rtc_get_priorities()

    def _rtc_get_priorities(self):

        try:
            resource_shapes = self.alm_plugin.call_api(self.resource_shape_url)
        except APIError, err:
            raise AlmException('Unable to get resource shapes')

        priorities = []
        for rs in resource_shapes['oslc:property']:
            if rs['oslc:name'] == 'priority':
                #print json.dumps(rs,indent=4)
                for p in rs['oslc:allowedValues']['oslc:allowedValue']:
                    priorities.append(self._get_priority_details(p['rdf:resource']))

        return priorities

    def _get_priority_details(self, priority_resource_url):

        priority_resource_url = priority_resource_url.replace(self.alm_plugin.base_uri+'/', '')
        try:
            priority_details = self.alm_plugin.call_api(priority_resource_url)
        except APIError, err:
            logger.error(err)
            raise AlmException('Unable to get priority details' % priority_resource_url)

        #print json.dumps(priority_details,indent=4)
        return priority_details

    def _get_priority_literal(self, priority_name):
        for priority in self.priorities:
            if priority['dcterms:title'] == priority_name:
                return priority['rdf:about']
        return None

    def get_item(self, query_str):

        target = '%s/%s' % (self.query_url, query_str)

        work_items = self.alm_plugin.call_api(target)

        #print json.dumps(work_items,indent=4)
        if work_items['oslc:responseInfo']['oslc:totalCount'] == 0:
            return None

        work_item_url = work_items['oslc:results'][0]['rdf:resource']
        work_item_target = work_item_url.replace(self.alm_plugin.base_uri+'/', '')

        return self.alm_plugin.call_api(work_item_target)

    def add_item(self, create_args):

        return self.alm_plugin.call_api(self.creation_url,
                                        method=self.alm_plugin.URLRequest.POST,
                                        args=create_args)

    def update_item(self, task, update_args):

        work_item_target = task.get_alm_url().replace(self.alm_plugin.base_uri+'/', '')
        self.alm_plugin.call_api(work_item_target, args=update_args, method=URLRequest.PUT)