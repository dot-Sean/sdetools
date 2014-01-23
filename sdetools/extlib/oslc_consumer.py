# Copyright SDElements Inc
# Extensible two way integration with OSLC

import json
from sdetools.sdelib.restclient import RESTBase
from sdetools.sdelib.restclient import URLRequest, APIError
from sdetools.alm_integration.alm_plugin_base import AlmConnector
from sdetools.alm_integration.alm_plugin_base import AlmException
from rdflib import Graph, RDF, RDFS, Namespace, Literal, term

from sdetools.sdelib import log_mgr
logger = log_mgr.mods.add_mod(__name__)
DCTERMS = Namespace("http://purl.org/dc/terms/")
OSLC = Namespace("http://open-services.net/ns/core#")

class OSLCAPI(RESTBase):

    """ Base plugin for OSLC Consumer """

    def __init__(self, config):
        super(OSLCAPI, self).__init__('alm', 'OSLC', config)
        #self.rdf_graph = Graph()

    def post_conf_init(self):
        super(OSLCAPI, self).post_conf_init()

    def encode_post_args(self, args):
        g = Graph()
        print args
        OSLC_CM = Namespace("http://open-services.net/ns/cm#")
        OSLC_CMX = Namespace("http://open-services.net/ns/cm-x#")
        try:
            g.add((OSLC_CM.changerequest, DCTERMS.identifier, Literal(args['id'])))
        except:
            pass
        try:
            g.add((OSLC_CM.changerequest, DCTERMS.title, Literal(args['dcterms:title'])))
        except:
            pass
        try:
            g.add((OSLC_CM.changerequest, OSLC_CMX.priority, Literal(args['oslc_cmx:priority'])))
        except:
            pass
        try:
            g.add((OSLC_CM.changerequest, DCTERMS.description, Literal(args['dcterms:description'])))
        except:
            pass
        try:
            g.add((OSLC_CM.changerequest, OSLC_CM.status, Literal(args['oslc_cm:status'])))
        except:
            pass
        return g.serialize()

    def call_api(self, target, method=URLRequest.GET, args=None, headers={'Accept': 'application/rdf+xml', 'OSLC-Core-Version': '2.0', 'Content-Type': 'application/rdf+xml'}):

        return super(OSLCAPI, self).call_api(target, method, args, headers)

    def parse_response(self, result, headers):
        print result
        print headers
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

        rdf_query = "SELECT ?y WHERE { ?y ?x ?z FILTER (?z = <http://open-services.net/ns/cm#>) }"
        uri = catalog.query(rdf_query).result[0][0].toPython()

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
        resource_url = None
        rdf_query = 'SELECT DISTINCT ?x WHERE {?x ?y ?z FILTER (str(?z) = "' + str(self.config['alm_project']) + '")}'
        #print rdf_query
        resource_url = service_catalog.query(rdf_query).result[0][0].toPython()
        if not resource_url:
            raise AlmException('Unable to connect retrieve resource url (Check server URL, user, pass).')

        resource_service = resource_url.replace(self.alm_plugin.base_uri+'/', '')
        services = self.alm_plugin.call_api(resource_service)
        # Find the lookup/query url

        query_query = "SELECT ?k WHERE {?x ?y ?z ; ?j ?k . FILTER (?y = <http://open-services.net/ns/core#usage> && ?j = <http://open-services.net/ns/core#queryBase> )}"
        query_url = services.query(query_query).result[0][0].toPython()
        #print query_url
        self.query_url = query_url.replace(self.alm_plugin.base_uri+'/', '')
        #print self.query_url

        # Find the resource shape url
        resource_shape_query = "SELECT ?k WHERE {?x ?y ?z ; ?j ?k . FILTER (?y = <http://open-services.net/ns/core#usage> && ?z = <http://open-services.net/ns/cm#task> && ?j = <http://open-services.net/ns/core#resourceShape>)}"
        resource_shape_url = services.query(resource_shape_query).result[0][0].toPython()
        self.resource_shape_url = resource_shape_url.replace(self.alm_plugin.base_uri+'/', '')

        # Find the creation url
        creation_query = "SELECT ?k WHERE {?x ?y ?z ; ?j ?k . FILTER (?j = <http://open-services.net/ns/core#creation> && ?z =<http://open-services.net/ns/cm#task>)}"
        creation_url = services.query(creation_query).result[0][0].toPython()
        self.creation_url = creation_url.replace(self.alm_plugin.base_uri+'/', '')

        # Grab the priorities
        self.priorities = self._rtc_get_priorities_not_plugin()

    def _rtc_get_priorities_not_plugin(self):

        try:
            resource_shapes = self.alm_plugin.call_api(self.resource_shape_url)
        except APIError, err:
            raise AlmException('Unable to get resource shapes')

        #  CHANGEME
        #priority_about = trunc_uri(resource_shapes.query('SELECT DISTINCT ?x WHERE {?x ?y ?z ; ?j ?k . FILTER (?z = <http://open-services.net/ns/cm-x#priority>)}').result[0])
        priority_allowed_val = resource_shapes.query('SELECT DISTINCT ?k WHERE {?x ?y ?z ; ?j ?k . FILTER (?z = <http://open-services.net/ns/cm-x#priority> && ?j = <http://open-services.net/ns/core#allowedValues>)}').result[0][0].toPython()
        #print priority_allowed_val
        priorities = []
        priority_allowed_val = priority_allowed_val.replace(self.alm_plugin.base_uri+'/', '')
        #print priority_allowed_val
        priority_literals = self.alm_plugin.call_api(priority_allowed_val)
        literals_list_temp = priority_literals.query('SELECT DISTINCT ?z WHERE {?x ?y ?z FILTER (?y = <http://open-services.net/ns/core#allowedValue>)}').result
        #print literals_list_temp
        for x in literals_list_temp:
            priority = self._get_priority_details(x[0].toPython())
            priority_name = priority.query('PREFIX dcterms: <http://purl.org/dc/terms/> SELECT ?z  WHERE {?x dcterms:title ?z}').result[0][0].toPython()
            priority_uri = priority.query('SELECT Distinct ?x WHERE {?x ?y ?z}').result[0][0].toPython()
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

    def _get_priority_literal(self, priority_name):
        try:
            return self.priorities[priority_name]
        except:
            return None

    def get_item(self, query_str):

        target = '%s/%s' % (self.query_url, query_str)

        work_items = self.alm_plugin.call_api(target)

        #print json.dumps(work_items,indent=4)
        #if work_items['oslc:responseInfo']['oslc:totalCount'] == 0:
        items_count = int(work_items.query('SELECT ?z WHERE {?x <http://open-services.net/ns/core#totalCount> ?z  }').result[0][0].toPython())
        #print type(items_count)
        if items_count == 0:
            return None

        #work_item_url = work_items['oslc:results'][0]['rdf:resource']
        work_item_url = work_items.query('SELECT ?z WHERE {?x <http://www.w3.org/2000/01/rdf-schema#member> ?z}').result[0][0].toPython()
        #print work_item_url
        work_item_target = work_item_url.replace(self.alm_plugin.base_uri+'/', '')
        workitem = self.alm_plugin.call_api(work_item_target)
        result = []
        date = workitem.query('PREFIX dcterms: <http://purl.org/dc/terms/> PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> SELECT ?z WHERE {?x dcterms:modified ?z} ').result[0][0].toPython()
        result.append(('modified', date))
        ident = workitem.query('PREFIX dcterms: <http://purl.org/dc/terms/> PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> SELECT ?z WHERE {?x dcterms:identifier ?z} ').result[0][0].toPython()
        result.append(('identifier', ident))
        about = workitem.query('select distinct ?x where {?x ?y ?z}').result[0][0].toPython()
        result.append(('about', about))
        status = workitem.query('select ?z where {?x <http://open-services.net/ns/cm#status> ?z}').result[0][0].toPython()
        result.append(('status', status))
        return dict(result)


    def add_item(self, create_args):

        return self.alm_plugin.call_api(self.creation_url,
                                        method=self.alm_plugin.URLRequest.POST,
                                        args=create_args)

    def update_item(self, task, update_args):

        work_item_target = task.get_alm_url().replace(self.alm_plugin.base_uri+'/', '')
        self.alm_plugin.call_api(work_item_target, args=update_args, method=URLRequest.PUT)