# Copyright SDElements Inc
# Extensible two way integration with HP Alm

import sys
import re
import cookielib
import urllib2
from datetime import datetime

from sdetools.sdelib.commons import json, urlencode_str

from sdetools.sdelib.restclient import RESTBase, APIError
from sdetools.alm_integration.alm_plugin_base import AlmTask, AlmConnector
from sdetools.alm_integration.alm_plugin_base import AlmException
from sdetools.sdelib.conf_mgr import Config
from sdetools.extlib import markdown, http_req

from sdetools.sdelib import log_mgr
logger = log_mgr.mods.add_mod(__name__)

URLRequest = http_req.ExtendedMethodRequest

HPALM_PRIORITY_MAP = {
    '10': '5-Urgent',
    '8-9': '4-Very High',
    '7': '3-High',
    '4-6': '2-Medium',
    '1-3': '1-Low',
    }


class HPAlmAPIBase(RESTBase):
    """ Base plugin for HP Alm """

    def __init__(self, config):
        super(HPAlmAPIBase, self).__init__('alm', 'HP Alm', config, 
                'qcbin')
        self.cookiejar = cookielib.CookieJar()

    def parse_response(self, result):
        if result == "":
            return "{}"
        else:
            return super(HPAlmAPIBase, self).parse_response(result)

    def post_conf_init(self):
        super(HPAlmAPIBase, self).post_conf_init()
        self.opener.add_handler(urllib2.HTTPCookieProcessor(self.cookiejar))

    def encode_post_args(self, args):
        if isinstance(args, basestring):
            return args
        else:
            return json.dumps(args)        
            
class HPAlmTask(AlmTask):
    """ Representation of a task in HP Alm """

    def __init__(self, task_id, alm_id, status, last_modified, done_statuses):
        self.task_id = task_id
        self.alm_id = alm_id
        self.timestamp = last_modified
        self.status = status
        self.done_statuses = done_statuses #comma-separated list

    def get_task_id(self):
        return self.task_id

    def get_alm_id(self):
        return self.alm_id

    def get_status(self):
        """Translates HP Alm status into SDE status"""
        if self.status in self.done_statuses:
            return 'DONE'
        else:
            return 'TODO'

    def get_timestamp(self):
        """ Returns a datetime object """
        return datetime.strptime(self.timestamp, '%Y-%m-%dT%H:%M:%SZ')

class HPAlmConnector(AlmConnector):
    """Connects SD Elements to HP Alm"""
    alm_name = 'HP Alm'

    def __init__(self, config, alm_plugin):
        super(HPAlmConnector, self).__init__(config, alm_plugin)

        """ Adds HP Alm specific config options to the config file"""
        config.add_custom_option('hp_alm_issue_type', 'IDs for issues raised in HP Alm',
            default='Functional')
        config.add_custom_option('hp_alm_new_status', 'status to set for new tasks in HP Alm',
            default='Not Completed')
        config.add_custom_option('hp_alm_done_statuses', 'Statuses that signify a task is Done in HP Alm',
            default='Passed')
        config.add_custom_option('hp_alm_domain', 'Domain', default=None)

    def initialize(self):
        super(HPAlmConnector, self).initialize()

        #Verify that the configuration options are set properly
        for item in ['hp_alm_done_statuses', 'hp_alm_issue_type', 'hp_alm_new_status', 'hp_alm_domain']:
            if not self.config[item]:
                raise AlmException('Missing %s in configuration' % item)

        self.config['hp_alm_done_statuses'] = (
                self.config['hp_alm_done_statuses'].split(','))

        self.COOKIE_LWSSO = None
        self.issue_type = None
        self.mark_down_converter = markdown.Markdown(safe_mode="escape")        

    def alm_connect_server(self):
        """ Verifies that HP Alm connection works """
        #Check to make sure that we can login
        try:
            self.alm_plugin.auth_mode = 'basic'
            self.alm_plugin.call_api('authentication-point/authenticate')
            for cookie in self.alm_plugin.cookiejar:
                if cookie.name == 'LWSSO_COOKIE_KEY':
                    self.COOKIE_LWSSO = cookie.value
        except APIError, err:
            raise AlmException('Unable to connect to HP Alm service (Check server URL, '
                    'user, pass). Reason: %s' % str(err))

        if not self.COOKIE_LWSSO:
            raise AlmException('Unable to connect to HP Alm service (Check server URL, user, pass)')

        # We will authenticate via cookie
        self.alm_plugin.auth_mode = 'cookie'
        
    def _call_api(self, target, query_args=None, method=URLRequest.GET):
        headers = {'Cookie':'LWSSO_COOKIE_KEY=%s' % self.COOKIE_LWSSO,
                   'Content-Type':'application/json',
                   'Accept':'application/json'}
        return self.alm_plugin.call_api(target, method=method, args=query_args, call_headers=headers)

    def _call_reqs_api(self, json, method=URLRequest.GET):
        return self._call_api('rest/domains/%s/projects/%s/requirements' 
                                    % (urlencode_str(self.config['hp_alm_domain']),
                                       urlencode_str(self.config['alm_project'])), method=method, query_args=json)
    
    def alm_connect_project(self):
        # Connect to the project
        try:
            user = self._call_api('rest/domains/%s/projects/%s/customization/users/%s' 
                                    % (urlencode_str(self.config['hp_alm_domain']),
                                       urlencode_str(self.config['alm_project']),
                                       urlencode_str(self.config['alm_user'])))
        except APIError, err:
            raise AlmException('Unable to verify domain and project details: %s' % (err))
        
        if user['Name'] != self.config['alm_user']:
            raise AlmException('Unable to verify user access to domain and project')

        # Get all the requirement types
        try:
            req_types = self._call_api('rest/domains/%s/projects/%s/customization/entities/requirement/types/' 
                                    % (urlencode_str(self.config['hp_alm_domain']),
                                       urlencode_str(self.config['alm_project'])))
        except APIError, err:
            raise AlmException('Unable to retrieve requirement types: %s' % (err)) 
        
        for req_type in req_types['types']:
            if req_type['name'] == self.config['hp_alm_issue_type']:
                self.issue_type = req_type['id']
                break

        if not self.issue_type:
            raise AlmException('Requirement type %s not found in project' % (self.config['hp_alm_issue_type'])) 

    def alm_get_task(self, task):
        task_id = self._extract_task_id(task['id'])  
        if not task_id:
            return None

        try:
            query_args = {
                'query': "{name['%s:*']}" % task_id,
                'fields': 'id,name,req-priority,status',
            }
            result = self._call_reqs_api(query_args)
                                               
        except APIError, err:
            raise AlmException('Unable to get task %s from HP Alm. '
                    'Reason: %s' % (task_id, str(err)))
        num_results = result['TotalResults']

        if not num_results:
            return None

        return self._get_hp_alm_task(task_id, result['entities'][0])

    def _get_hp_alm_task(self, task_id, task_data):
        hp_alm_id = None
        hp_alm_status = None
        hp_alm_last_update = None
        hp_alm_title = None
        hp_alm_last_modified = None

        for field in task_data['Fields']:
            if field['Name'] == 'id':
                hp_alm_id = field['values'][0]['value']
            elif field['Name'] == 'status':
                hp_alm_status = field['values'][0]['value']
            elif field['Name'] == 'name':
                hp_alm_title = field['values'][0]['value']
            elif field['Name'] == 'last-modified':
                hp_alm_last_modified = field['values'][0]['value']

        return HPAlmTask(task_id,
                         hp_alm_id,
                         hp_alm_status,
                         hp_alm_last_modified,
                         self.config['hp_alm_done_statuses'])
                   
    def _extract_task_id(self, full_task_id):
        task_id = None
        task_search = re.search('^(\d+)-([^\d]+\d+)$', full_task_id)
        if task_search:
            task_id = task_search.group(2)    
        return task_id

    def alm_add_task(self, task):
        task_id = self._extract_task_id(task['id'])  
        if not task_id:
            return None

        task['formatted_content'] = self.sde_get_task_content(task)
        task['alm_priority'] = self.translate_priority(task['priority'])

        # HP Alm is very particular about JSON ordering - we must hand-craft it            
        json_data = """{
            "Fields":[
                {"Name":"type-id","values":[{"value":%s}]},
                {"Name":"status","values":[{"value":%s}]},
                {"Name":"name","values":[{"value":%s}]},
                {"Name":"description","values":[{"value":%s}]},
                {"Name":"req-priority","values":[{"value":%s}]}
            ], 
            "Type":"requirement"
        }""" % (json.dumps(self.issue_type), json.dumps(self.config['hp_alm_new_status']), json.dumps(task['title']),
                json.dumps(task['formatted_content']), json.dumps(task['alm_priority']))
        try:
            result = self._call_reqs_api(json_data, self.alm_plugin.URLRequest.POST)
            logger.debug('Task %s added to HP Alm Project', task['id'])
        except APIError, err:
            raise AlmException('Unable to add task to HP Alm %s because of %s' % 
                    (task['id'], err))

        alm_task = self._get_hp_alm_task(task_id, result)
        
        if (self.config['alm_standard_workflow'] and
            (task['status'] == 'DONE' or task['status'] == 'NA')):
            self.alm_update_task_status(alm_task, task['status'])
        
        return "Req ID %s" % alm_task.get_alm_id()

    def alm_update_task_status(self, task, status):

        if not task or not self.config['alm_standard_workflow']:
            logger.debug('Status synchronization disabled')
            return

        if status == 'DONE' or status == 'NA':
            json_data = """
                {"entities":[{"Fields":[
                {"Name":"id","values":[{"value":%s}]},
                {"Name":"status","values":[{"value":%s}]}
                ]}]}""" % (json.dumps(task.get_alm_id()), json.dumps(self.config['hp_alm_done_statuses'][0]))
            status = "DONE"

        elif status == 'TODO':
            json_data = """
                {"entities":[{"Fields":[
                {"Name":"id","values":[{"value":%s}]},
                {"Name":"status","values":[{"value":%s}]}
                ]}]}""" % (json.dumps(task.get_alm_id()), json.dumps(self.config['hp_alm_new_status']))
        else:
            raise AlmException('Unexpected status %s: valid values are DONE and TODO' % status)

        try:
            result = self._call_reqs_api(json_data, self.alm_plugin.URLRequest.PUT)
        except APIError, err:
            raise AlmException('Unable to update task status to %s '
                               'for requirement: '
                               '%s in HP Alm because of %s' %
                               (status, task.get_alm_id(), err))

        logger.debug('Status changed to %s for task %s in HP Alm',
                      status, task.get_alm_id())

    def alm_disconnect(self):
        try:
            result = self._call_api('authentication-point/logout')
        except APIError, err:
            logger.warn('Unable to logout from HP Alm. Reason: %s' % (str(err)))

    def convert_markdown_to_alm(self, content, ref): 
        return '<html>'+self.mark_down_converter.convert(content)+'</html>'

    def translate_priority(self, priority):
        """ Translates an SDE priority into a HP ALM priority """
        try:
            priority = int(priority)
        except (TypeError):
            logger.error('Could not coerce %s into an integer' % priority)
            raise AlmException("Error in translating SDE priority to HP Alm: "
                               "%s is not an integer priority" % priority)
        pmap = HPALM_PRIORITY_MAP
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
