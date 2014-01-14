# Copyright SDElements Inc
# Extensible two way integration with OSLC

import json
from sdetools.sdelib.restclient import RESTBase
from sdetools.sdelib.restclient import URLRequest, APIError
from sdetools.alm_integration.alm_plugin_base import AlmConnector
from sdetools.alm_integration.alm_plugin_base import AlmException
from rdflib import Graph, term

from sdetools.sdelib import log_mgr
logger = log_mgr.mods.add_mod(__name__)

class OSLCAPI(RESTBase):

    """ Base plugin for OSLC Consumer """

    def __init__(self, config):
        super(OSLCAPI, self).__init__('alm', 'OSLC', config)
        #self.rdf_graph = Graph()

    def post_conf_init(self):
        super(OSLCAPI, self).post_conf_init()

    def call_api(self, target, method=URLRequest.GET, args=None):

        headers = {'Accept': 'application/rdf+xml', 'OSLC-Core-Version': '2.0', 'Content-Type': 'application/rdf+xml'}
        return super(OSLCAPI, self).call_api(target, method, args, headers)

    def parse_response(self, result):
        #print result
        try:
            result = Graph().parse(data=result)
        except Exception, e:
            logger.error('Error parsing rdf+xml: %s' % e)
            raise AlmException('Unable to process RDF+XML data: %s' % str(result)[:200])
        return result

    def parse_error(self, result):
        try:
            error = self.rdf_graph.parse(result)
        except:
            raise AlmException('Unable to process RDF+XML data: %s' % str(result)[:200])
        return error


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
        #for s, p, o in catalog:
        #    print s, p, o
        #print list(catalog.subjects())

        rdf_query = "SELECT ?y WHERE { ?y ?x ?z FILTER (?z = <http://open-services.net/ns/cm#>) }"
        uri = list(catalog.query(rdf_query))[0][0].toPython()

        #subj = term.URIRef(self.alm_plugin.base_uri+'/rootservices')
        #pred = term.URIRef(self.OSLC_SERVICE_PROVIDER)
        #objs = self.alm_plugin.rdf_graph.value(subject=subj, predicate=pred)
        #self.service_provider_uri = catalog.value(subject=subj, predicate=pred)
        self.service_provider_uri = uri

        if not self.service_provider_uri:
            raise AlmException('Service provider not found (Check server URL, user, pass).')

        base_uri_end = len(self.alm_plugin.base_uri)+1

        service_provider_target = uri[base_uri_end:]
        #print service_provider_target
        del base_uri_end
        try:
            service_catalog = self.alm_plugin.call_api(service_provider_target)
        except APIError, err:
            raise AlmException('Unable to connect retrieve service catalog (Check server URL, user, pass).'
                               'Reason: %s' % str(err))
        if not service_catalog:
            raise AlmException('Unable to connect retrieve service catalog (Check server URL, user, pass).')

        del uri
        #for s, p, o in service_catalog:
        #    print s, p, o
        #print list(service_catalog)
        resource_url = None
        #for service_provider in service_catalog['oslc:serviceProvider']:
        #    if service_provider['dc:title'] == self.config['alm_project']:
        #        resource_url = service_provider['rdf:about']

        #pred = term.URIRef("http://purl.org/dc/terms/title")
        #obj = term.Literal(self.config['alm_project'],
        #                   datatype=term.URIRef(u'http://www.w3.org/1999/02/22-rdf-syntax-ns#XMLLiteral'))
        #print "START TEST"
        #print str(self.config['alm_project'])
        rdf_query = 'SELECT DISTINCT ?x WHERE {?x ?y ?z FILTER (str(?z) = "' + str(self.config['alm_project']) + '")}'
        #print rdf_query
        resource_url = list(service_catalog.query(rdf_query))[0][0].toPython()
        #print list(resource_url)
        #oo = list(resource_url)[0]
        #uri = trunc_uri(str(oo))
        #print uri
        #print "END TEST"
        #resource_url = uri
        if not resource_url:
            raise AlmException('Unable to connect retrieve resource url (Check server URL, user, pass).')

        resource_service = resource_url.replace(self.alm_plugin.base_uri+'/', '')
        #import pprint
        #pprint.pprint(resource_service)
        services = self.alm_plugin.call_api(resource_service)
        #print json.dumps(services['oslc:service'][1], indent=4)
        #for s, p, o in services:
        #    print s, p, o
        #print list(services)

        #pred = term.URIRef("http://open-services.net/ns/core#usage")
        #obj = term.URIRef(self.OSLC_TYPE)

        #bnode = services.value(predicate=pred, object=obj)
        #subj = bnode

        # Find the lookup/query url

        query_query = "SELECT ?x ?y ?z ?j ?k WHERE {?x ?y ?z ; ?j ?k . FILTER (?y = <http://open-services.net/ns/core#usage> && ?j = <http://open-services.net/ns/core#queryBase> )}"
        query_url = list(services.query(query_query))[0][0].toPython()
        self.query_url = query_url.replace(self.alm_plugin.base_uri+'/', '')

        # Find the resource shape url
        resource_shape_query = "SELECT ?k WHERE {?x ?y ?z ; ?j ?k . FILTER (?y = <http://open-services.net/ns/core#usage> && ?z = <http://open-services.net/ns/cm#task> && ?j = <http://open-services.net/ns/core#resourceShape>)}"
        resource_shape_url = list(services.query(resource_shape_query))[0][0].toPython()
        self.resource_shape_url = resource_shape_url.replace(self.alm_plugin.base_uri+'/', '')

        # Find the creation url
        creation_query = "SELECT ?k WHERE {?x ?y ?z ; ?j ?k . FILTER (?j = <http://open-services.net/ns/core#creation> && ?z =<http://open-services.net/ns/cm#task>)}"
        creation_url = list(services.query(creation_query))[0][0].toPython()
        self.creation_url = creation_url.replace(self.alm_plugin.base_uri+'/', '')

        # Grab the priorities
        self.priorities = self._rtc_get_priorities_not_plugin()

    def _rtc_get_priorities_not_plugin(self):

        try:
            resource_shapes = self.alm_plugin.call_api(self.resource_shape_url)
        except APIError, err:
            raise AlmException('Unable to get resource shapes')

        #  CHANGEME
        #priority_about = trunc_uri(list(resource_shapes.query('SELECT DISTINCT ?x WHERE {?x ?y ?z ; ?j ?k . FILTER (?z = <http://open-services.net/ns/cm-x#priority>)}'))[0])
        priority_allowed_val = list(resource_shapes.query('SELECT DISTINCT ?k WHERE {?x ?y ?z ; ?j ?k . FILTER (?z = <http://open-services.net/ns/cm-x#priority> && ?j = <http://open-services.net/ns/core#allowedValues>)}'))[0][0].toPython()
        #print priority_allowed_val
        priorities = []
        priority_allowed_val = priority_allowed_val.replace(self.alm_plugin.base_uri+'/', '')
        #print priority_allowed_val
        priority_literals = self.alm_plugin.call_api(priority_allowed_val)
        literals_list_temp = list(priority_literals.query('SELECT DISTINCT ?z WHERE {?x ?y ?z FILTER (?y = <http://open-services.net/ns/core#allowedValue>)}'))
        #print literals_list_temp
        for x in literals_list_temp:
            priority = self._get_priority_details(x[0].toPython())
            priority_name = list(priority.query('PREFIX dcterms: <http://purl.org/dc/terms/> SELECT ?z  WHERE {?x dcterms:title ?z}'))[0][0].toPython()
            priority_uri = list(priority.query('SELECT Distinct ?x WHERE {?x ?y ?z}'))[0][0].toPython()
            #print priority_name
            priorities.append((priority_name, priority_uri))
        del literals_list_temp
        priorities = dict(priorities)
        #print priorities

        #for rs in resource_shapes['oslc:property']:
        #    if rs['oslc:name'] == 'priority':
        #        #print json.dumps(rs,indent=4)
        #        for p in rs['oslc:allowedValues']['oslc:allowedValue']:
        #            priorities.append(self._get_priority_details(p['rdf:resource']))

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

    #def _get_priority_literal(self, priority_name):
    #    for priority in self.priorities:
    #        if priority['dcterms:title'] == priority_name:
    #            return priority['rdf:about']
    #    return None

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