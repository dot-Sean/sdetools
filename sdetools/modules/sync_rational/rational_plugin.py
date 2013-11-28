# Copyright SDElements Inc
# Extensible two way integration with Rational

import re, json
from datetime import datetime

from sdetools.extlib import http_req
from sdetools.extlib.defusedxml import minidom
from sdetools.sdelib.commons import urlencode_str
from sdetools.sdelib.restclient import RESTBase
from sdetools.sdelib.restclient import URLRequest, APIError
from sdetools.alm_integration.alm_plugin_base import AlmTask, AlmConnector
from sdetools.alm_integration.alm_plugin_base import AlmException
from sdetools.extlib.oslc_consumer import OSLCConnector

from sdetools.sdelib import log_mgr
logger = log_mgr.mods.add_mod(__name__)

RE_MAP_RANGE_KEY = re.compile('^\d+(-\d+)?$')
RATIONAL_DEFAULT_PRIORITY_MAP = {
    '7-10': 'High',
    '4-6': 'Medium',
    '1-3': 'Low',
    }


class RationalAPI(RESTBase):
    """ Base plugin for Rational """

    def __init__(self, config):
        #base_path = config['rational_context_root']
        super(RationalAPI, self).__init__('alm', 'Rational', config, "sandbox01-ccm")


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
        return datetime.strptime(self.timestamp, '%Y-%m-%dT%H:%M:%SZ')


class RationalConnector(OSLCConnector):
    alm_name = 'Rational'
    OSLC_APP_NAME = "RTC"
    OSLC_SERVICE_PROVIDER = 'http://open-services.net/xmlns/cm/1.0/cmServiceProviders'
    OSLC_TYPE = "http://open-services.net/ns/cm#task"
    cm_service_provider = None
    resource_url = None
    priorities = None
    ALM_NEW_STATUS = 'rational_new_status'
    ALM_DONE_STATUSES = 'rational_done_statuses'

    def __init__(self, config, alm_plugin):
        """ Initializes connection to Rational """
        super(RationalConnector, self).__init__(config, alm_plugin)

        config.add_custom_option(self.ALM_NEW_STATUS, 'Status to set for new'
                                 'tasks in Rational', default='New')
        config.add_custom_option(self.ALM_DONE_STATUSES, 'Statuses that '
                                 'signify a task is Done in Rational',
                                 default='Complete,Done')

    def initialize(self):
        super(RationalConnector, self).initialize()

        # Verify that the configuration options are set properly
        for item in [self.ALM_NEW_STATUS, self.ALM_DONE_STATUSES]:
            if not self.config[item]:
                raise AlmException('Missing %s in configuration' % item)

        self.config[self.ALM_DONE_STATUSES] = self.config[self.ALM_DONE_STATUSES].split(',')

        self.config.process_json_str_dict(self.ALM_PRIORITY_MAP)

        if not self.config[self.ALM_PRIORITY_MAP]:
            self.config[self.ALM_PRIORITY_MAP] = RATIONAL_DEFAULT_PRIORITY_MAP

        for key in self.config[self.ALM_PRIORITY_MAP]:
            if not RE_MAP_RANGE_KEY.match(key):
                raise AlmException('Unable to process %s (not a JSON dictionary). Reason: Invalid range key %s'
                                   % (self.ALM_PRIORITY_MAP, key))

    def alm_connect_server(self):
        super(RationalConnector, self).alm_connect_server()

    def _rtc_get_priorities(self):

        try:
            resource_shapes = self.alm_plugin.call_api(self.resource_shape_url)
        except APIError, err:
            logger.error(err)
            raise AlmException('Unable to get resource shapes from Rational')

        priorities = []
        for rs in resource_shapes['oslc:property']:
            if rs['oslc:name'] == 'priority':
                #print json.dumps(rs,indent=4)
                for p in rs['oslc:allowedValues']['oslc:allowedValue']:
                    priorities.append(self._rtc_get_priority_details(p['rdf:resource']))

        return priorities

    def _rtc_get_priority_details(self, priority_resource_url):

        priority_resource_url = priority_resource_url.replace(self.alm_plugin.base_uri+'/', '')

        try:
            priority_details = self.alm_plugin.call_api(priority_resource_url)
        except APIError, err:
            logger.error(err)
            raise AlmException('Unable to get priority details from Rational' % priority_resource_url)

        #print json.dumps(priority_details,indent=4)
        return priority_details

    def alm_connect_project(self):
        """ Verifies that the Rational project exists """

    def _extract_task_id(self, full_task_id):
        task_id = None
        task_search = re.search('^(\d+)-([^\d]+\d+)$', full_task_id)
        if task_search:
            task_id = task_search.group(2)
        return task_id

    def alm_get_task(self, task):
        task_id = self._extract_task_id(task['id'])
        if not task_id:
            return None

        query_str = ('workitems?oslc.where=dcterms:title="%s:*"' % task_id)

        try:
            work_item = super(RationalConnector, self).get_item(query_str)
        except APIError, err:
            logger.error(err)
            raise AlmException('Unable to get task %s from Rational' % task_id)

        if not work_item:
            return work_item

        logger.info('Found task: %s', task_id)
        return RationalTask(task_id,
                                  work_item['rdf:about'],
                                  work_item['dcterms:identifier'],
                                  work_item['oslc_cm:status'],
                                  work_item['dcterms:modified'],
                                  self.config[self.ALM_DONE_STATUSES])

    def alm_add_task(self, task):

        priority_name = self.translate_priority(task['priority'])
        priority_literal_resource = super(RationalConnector, self)._get_priority_literal(priority_name)

        create_args = {
            'dcterms:title': task['title'],
            'dcterms:description': "This is content",
            'oslc_cmx:priority': priority_literal_resource,
        }

        try:
            work_item = super(RationalConnector, self).add_item(create_args)
            logger.debug('Task %s added to RTC', task['id'])
        except APIError, err:
            raise AlmException('Unable to add task %s to RTC because of %s'
                               % (task['id'], err))

        #print json.dumps(work_item,indent=4)
        # API returns JSON of the new issue
        alm_task = RationalTask(task['title'],
                                      None, # try to fill this in later
                                      work_item['dcterms:identifier'],
                                      work_item['oslc_cm:status'],
                                      work_item['dcterms:modified'],
                                      self.config[self.ALM_DONE_STATUSES])

        if (self.config['alm_standard_workflow'] and
                (task['status'] == 'DONE' or task['status'] == 'NA')):
            self.alm_update_task_status(alm_task, task['status'])

        return 'Project: %s, Task: %s' % (self.config['alm_project'], alm_task.get_alm_id())

    def alm_update_task_status(self, task, status):
        if not task or not self.config['alm_standard_workflow']:
            logger.debug('Status synchronization disabled')
            return

        if status == 'DONE' or status == 'NA':
            alm_state = self.config[self.ALM_DONE_STATUSES][0]
        elif status == 'TODO':
            alm_state = self.config[self.ALM_NEW_STATUS]

        update_args = {
            'oslc_cm:status': alm_state
        }

        try:
            result = super(RationalConnector, self).update_item(task, update_args)
        except APIError, err:
            raise AlmException('Unable to update status to %s '
                               'for task: %s in Rational because of %s' %
                               (status, task.get_alm_id(), err))

        logger.debug('Task changed to %s for task %s in PivotalTracker' %
                     (status, task.get_alm_id()))

    def alm_disconnect(self):
        pass

    def translate_priority(self, priority):
        """ Translates an SDE priority into a GitHub label """
        pmap = self.config[self.ALM_PRIORITY_MAP]

        if not pmap:
            return None

        try:
            priority = int(priority)
        except TypeError:
            logger.error('Could not coerce %s into an integer' % priority)
            raise AlmException("Error in translating SDE priority to GitHub label: "
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