# Copyright SDElements Inc
# Extensible two way integration with HP Alm

import sys
import re
from datetime import datetime

from sdetools.sdelib.commons import json

from sdetools.sdelib.restclient import RESTBase, APIError
from sdetools.alm_integration.alm_plugin_base import AlmTask, AlmConnector
from sdetools.alm_integration.alm_plugin_base import AlmException
from sdetools.sdelib.conf_mgr import Config
from sdetools.extlib import markdown

from sdetools.sdelib import log_mgr
logger = log_mgr.mods.add_mod(__name__)

MAX_CONTENT_SIZE = 30000

HPALM_HTML_CONVERT = [
    ('<h1>', '<br><font size="5">'),
    ('<h2>', '<br><font size="4">'),
    ('<h3>', '<br><font size="3">'),
    ('<h4>', '<br><font size="2">'),
    ('<h5>', '<br><font size="2">'),
    ('<h6>', '<br><font size="2">'),
    (re.compile('</h[1-6]>'), '</font><br><br>'),
    ('\n', ''),
    ('"', '\"'),
    ('<p>', ''),
    ('</p>', '<br><br>'),
    ('<pre><code>', '<span style="font-family: courier new,monospace;"><pre><code>'),
    ('</code></pre>', '</code></pre></span>'),
]

class HPAlmAPIBase(RESTBase):
    """ Base plugin for HP Alm """

    def __init__(self, config):
        super(HPAlmAPIBase, self).__init__('alm', 'HPAlm', config, 
                'qcbin')

    def parse_response(self, result):
        if result == "":
            return "{}"
        else:
            return super(HPAlmAPIBase, self).parse_response(result)
                
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

    def get_alm_task_ref(self):
        return self.alm_task_ref

    def get_alm_id(self):
        return self.alm_id

    def get_priority(self):
        return None

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
            default='3')
        config.add_custom_option('hp_alm_new_status', 'status to set for new tasks in HP Alm',
            default='Not Covered')
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

        self.project_ref = None
        self.domain_ref = None
        self.COOKIE_LWSSO = None

        self.mark_down_converter = markdown.Markdown(safe_mode="escape")        

    def carriage_return(self):
        return '<br//>'

    def alm_connect_server(self):
        """ Verifies that Rally connection works """
        #Check to make sure that we can do a simple API call
        try:
            self.alm_plugin.auth_mode = 'basic'
            self.alm_plugin.call_api('authentication-point/authenticate')
            for cookie in self.alm_plugin.cookiejar:
                if cookie.name == 'LWSSO_COOKIE_KEY':
                    self.COOKIE_LWSSO = cookie.value
        except APIError, err:
            raise AlmException('Unable to connect to HP Alm service (Check server URL, '
                    'user, pass). Reason: %s' % str(err))

    def alm_connect_project(self):
        pass

    def alm_get_task(self, task):
        task_id = None
        task_search = re.search('^(\d+)-([^\d]+\d+)$', task['id'])
        if task_search:
            task_id = task_search.group(2)    
        
        if not task_id:
            return None

        try:
            query_args = {
                'alt':'application/json',
                'query': "{name['%s:*']}" % task_id,
                'fields': 'id,name,req-priority,status',
                }
            headers = {'Cookie':'LWSSO_COOKIE_KEY=%s' % self.COOKIE_LWSSO}
            result = self.alm_plugin.call_api('rest/domains/%s/projects/%s/requirements' 
                                        % (self.config['hp_alm_domain'], self.config['alm_project']),
                                               args = query_args, call_headers=headers)
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
                         
    def alm_add_task(self, task):
        task_id = None
        task_search = re.search('^(\d+)-([^\d]+\d+)$', task['id'])
        if task_search:
            task_id = task_search.group(2)    
        
        if not task_id:
            return None

        # HP Alm is very particular about JSON ordering
        query_args = """{
            "Fields":[
                {"Name":"type-id","values":[{"value":"3"}]},
                {"Name":"status","values":[{"value":"Not Covered"}]},
                {"Name":"name","values":[{"value":"%s"}]},
                {"Name":"description","values":[{"value":"%s"}]},
                {"Name":"req-priority","values":[{"value":"5-Urgent"}]}
            ], 
            "Type":"requirement"
        }""" % (task['title'], self.sde_get_task_content(task))
        try:
            headers = {'Cookie':'LWSSO_COOKIE_KEY=%s' % self.COOKIE_LWSSO,
                       'Content-Type':'application/json',
                       'Accept':'application/json'}
            result = self.alm_plugin.call_api('rest/domains/%s/projects/%s/requirements' 
                                        % (self.config['hp_alm_domain'], self.config['alm_project']),
                                        method = self.alm_plugin.URLRequest.POST, args = query_args, 
                                        call_headers=headers)
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

        headers = {'Cookie':'LWSSO_COOKIE_KEY=%s' % self.COOKIE_LWSSO,
                   'Content-Type':'application/json',
                   'Accept':'application/json'}
                   
        if status == 'DONE' or status == 'NA':
            try:
                query_args = """
                    {"entities":[{"Fields":[
                    {"Name":"id","values":[{"value":"%s"}]},
                    {"Name":"status","values":[{"value":"Passed"}]}
                    ]}]}""" % task.get_alm_id()

                self.alm_plugin.call_api('rest/domains/%s/projects/%s/requirements' 
                                        % (self.config['hp_alm_domain'], self.config['alm_project']),
                                          args = query_args,
                                          method=self.alm_plugin.URLRequest.PUT,
                                          call_headers=headers)
            except APIError, err:
                raise AlmException('Unable to update task status to DONE '
                                   'for card: %s in HP Alm because of %s' % 
                                   (task.get_alm_id(), err))

        elif status == 'TODO':
            try:
                query_args = """
                    {"entities":[{"Fields":[
                    {"Name":"id","values":[{"value":"%s"}]},
                    {"Name":"status","values":[{"value":"Not Covered"}]}
                    ]}]}""" % task.get_alm_id()
                self.alm_plugin.call_api('rest/domains/%s/projects/%s/requirements' 
                                        % (self.config['hp_alm_domain'], self.config['alm_project']),
                                          args = query_args,
                                          method=self.alm_plugin.URLRequest.PUT,
                                          call_headers=headers)
            except APIError, err:
                raise AlmException('Unable to update task status to TODO '
                                   'for card: '
                                   '%s in HP Alm because of %s' %
                                   (task.get_alm_id(), err))

        logger.debug('Status changed to %s for task %s in HP Alm',
                      status, task.get_alm_id())

    def alm_disconnect(self):
        pass

    def sde_get_task_content(self, task):
        """ Convenience method that returns the text that should go into
        content of an ALM ticket/defect/story for a given task.

        Raises an AlmException on encountering an error

        Keyword arguments:
        task  -- An SD Elements task representing the task to enter in the
                 ALM
        """
        content = '%s\n\nImported from SD Elements' % (task['content'])
        return self.convert_markdown_to_alm(content, ref=task['id'])

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

        for before, after in HPALM_HTML_CONVERT:
            if type(before) is str:
                s = s.replace(before, after)
            else:
                s = before.sub(after, s)

        if len(s) > MAX_CONTENT_SIZE:
            logger.warning('Content too long for %s - Truncating.' % ref)
            s = s[:MAX_CONTENT_SIZE]

        return s.replace('"','\"')
