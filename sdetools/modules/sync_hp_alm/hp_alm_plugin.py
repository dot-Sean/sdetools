# Copyright SDElements Inc
# Extensible two way integration with HP Alm

from datetime import datetime
from types import ListType
from sdetools.sdelib.commons import json, urlencode_str
from sdetools.sdelib.restclient import RESTBase, APIError
from sdetools.alm_integration.alm_plugin_base import AlmTask, AlmConnector
from sdetools.alm_integration.alm_plugin_base import AlmException
from sdetools.extlib import markdown, http_req
from sdetools.sdelib import log_mgr

logger = log_mgr.mods.add_mod(__name__)

URLRequest = http_req.ExtendedMethodRequest

HPALM_PRIORITY_MAP = {
    '9-10': '5-Urgent',
    '7-8': '4-Very High',
    '5-6': '3-High',
    '3-4': '2-Medium',
    '1-2': '1-Low',
}


class HPAlmAPIBase(RESTBase):
    """ Base plugin for HP Alm """

    def __init__(self, config):
        super(HPAlmAPIBase, self).__init__('alm', 'HP Alm', config, 'qcbin')

    def parse_response(self, result):
        if result == "":
            return "{}"
        else:
            parsed_response = super(HPAlmAPIBase, self).parse_response(result)

            if parsed_response.get('entities'):
                # Entity collection
                parsed_response['entities'] = self._parse_entity_collection(parsed_response['entities'])
            elif parsed_response.get('Fields'):
                # Single Entity
                parsed_response = self._parse_entity_collection([parsed_response])[0]
            return parsed_response

    def encode_post_args(self, args):
        if isinstance(args, basestring):
            return args
        else:
            return super(HPAlmAPIBase, self).encode_post_args(args)

    @staticmethod
    def _parse_entity_collection(entities):
        """
            Clean-up the entities collection to make it easier to access field values
        """
        ret = []
        for entity in entities:
            entity_obj = {
                'fields': {},
                'type': entity['Type']
            }

            for field in entity['Fields']:
                entity_obj['fields'][field['Name']] = [v.get('value') for v in field['values']]
            ret.append(entity_obj)

        return ret


class HPAlmTask(AlmTask):
    """ Representation of a task in HP Alm """

    def __init__(self, task_id, alm_id, status, last_modified, done_statuses):
        self.task_id = task_id
        self.alm_id = alm_id
        self.timestamp = last_modified
        self.status = status
        self.done_statuses = done_statuses  # comma-separated list

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
        config.add_custom_option('hp_alm_reopen_status', 'status to set to reopen a task in HP Alm',
                                 default='Not Completed')
        config.add_custom_option('hp_alm_close_status', 'status to set to close a task in HP Alm',
                                 default='Passed')
        config.add_custom_option('hp_alm_done_statuses', 'Statuses that signify a task is Done in HP Alm',
                                 default='Passed')
        config.add_custom_option('hp_alm_domain', 'Domain',
                                 default=None)
        config.add_custom_option('hp_alm_test_plan_folder', 'Test plan folder where we import our test tasks',
                                 default='SD Elements')
        config.add_custom_option('hp_alm_test_type', 'Default type for new test tasks',
                                 default='MANUAL')

    def initialize(self):
        super(HPAlmConnector, self).initialize()
        #Verify that the configuration options are set properly
        for item in ['hp_alm_done_statuses', 'hp_alm_issue_type', 'hp_alm_new_status', 'hp_alm_domain']:
            if not self.config[item]:
                raise AlmException('Missing %s in configuration' % item)

        self.config.process_list_config('hp_alm_done_statuses')
        self.COOKIE_LWSSO = None
        self.issue_type = None
        self.mark_down_converter = markdown.Markdown(safe_mode="escape")
        self.project_uri = 'rest/domains/%s/projects/%s' % (urlencode_str(self.config['hp_alm_domain']),
                                                            urlencode_str(self.config['alm_project']))
        #We will map the requirement to the tests based on the cwe_id
        self.requirement_to_test_mapping = {}

    def alm_connect_server(self):
        """ Verifies that HP Alm connection works """
        # We will authenticate via cookie
        self.alm_plugin.set_auth_mode('cookie')

        #Check to make sure that we can login
        try:
            self.alm_plugin.call_api('authentication-point/authenticate', auth_mode='basic')
        except APIError, err:
            raise AlmException('Unable to connect to HP Alm service (Check server URL, '
                               'user, pass). Reason: %s' % str(err))

        for cookie in self.alm_plugin.cookiejar:
            if cookie.name == 'LWSSO_COOKIE_KEY':
                self.COOKIE_LWSSO = cookie.value

        if not self.COOKIE_LWSSO:
            raise AlmException('Unable to connect to HP Alm service (Check server URL, user, pass)')

    def _call_api(self, target, query_args=None, method=URLRequest.GET):
        headers = {'Cookie': 'LWSSO_COOKIE_KEY=%s' % self.COOKIE_LWSSO,
                   'Content-Type': 'application/json',
                   'Accept': 'application/json'}
        return self.alm_plugin.call_api(target, method=method, args=query_args, call_headers=headers)

    def _call_reqs_api(self, json, method=URLRequest.GET):
        return self._call_api('%s/requirements' % self.project_uri, method=method, query_args=json)

    def _call_test_api(self, json, method=URLRequest.GET):
        return self._call_api('%s/tests' % self.project_uri, method=method, query_args=json)

    def alm_connect_project(self):
        # Connect to the project
        try:
            user = self._call_api('%s/customization/users/%s' % (self.project_uri, urlencode_str(self.config['alm_user'])))
        except APIError, err:
            raise AlmException('Unable to verify domain and project details: %s' % (err))

        if user['Name'] != self.config['alm_user']:
            raise AlmException('Unable to verify user access to domain and project')
        logger.info(user)
        # Get all the requirement types
        self.validate_configurations()
        self.test_plan_folder_id = self._fetch_test_plan_folder_id("{name['%s']}" % self.config['hp_alm_test_plan_folder'])
        if not self.test_plan_folder_id:
            raise Exception('expected')

    def alm_get_task(self, task):
        task_id = self._extract_task_id(task['id'])

        if not task_id:
            return None
        if task['phase'] != 'testing':
            logger.info(task['weakness'])
            entity_type = 'requirements'
            entity_status_field = 'status'
        else:
            entity_type = 'tests'
            entity_status_field = 'exec-status'

        query_args = {
            'query': "{name['%s-*']}" % task_id,
            'fields': 'id,name,last-modified,%s' % entity_status_field
        }

        try:
            result = self._call_api('%s/%s' % (self.project_uri, entity_type), query_args=query_args)
        except APIError, err:
            raise AlmException('Unable to get task %s from HP Alm. Reason: %s' % (task_id, str(err)))

        if not result['TotalResults'] > 0:
            return None

        if entity_status_field == 'exec-status':
            logger.debug(result['entities'][0]['fields'][entity_status_field][0])

        return HPAlmTask(task_id,
                         result['entities'][0]['fields']['id'][0],
                         result['entities'][0]['fields'][entity_status_field][0],
                         result['entities'][0]['fields']['last-modified'][0],
                         self.config['hp_alm_done_statuses'])

    def alm_add_task(self, task):
        task_id = self._extract_task_id(task['id'])
        if not task_id:
            return None

        if task['phase'] != "testing":
            return self._alm_add_requirement(task, task_id)
        else:
            return self._alm_add_test(task, task_id)

    def _alm_add_test(self, task, task_id):
        if self.test_plan_folder_id is None:
            self.test_plan_folder_id = self._create_test_plan_folder()

        field_data = [
            ('name', task['title'].replace(':', '-')),
            ('description', self.sde_get_task_content(task)),
            ('parent-id', self.test_plan_folder_id),
            ('subtype-id', self.config['hp_alm_test_type']),
            ('owner', self.config['alm_user']),
            ('status', 'Imported')
        ]
        json_data = """%s""" % self._build_json_args(field_data, 'test')

        try:
            result = self._call_test_api(json_data, self.alm_plugin.URLRequest.POST)
        except APIError, err:
            raise AlmException('Unable to add task to HP Alm %s because of %s' %
                               (task['id'], err))

        logger.debug('Task %s added to HP Alm Project', task['id'])

        alm_task = HPAlmTask(task_id,
                             result['fields']['id'][0],
                             result['fields']['status'][0],
                             result['fields']['last-modified'][0],
                             self.config['hp_alm_done_statuses'])

        if (self.config['alm_standard_workflow'] and (task['status'] == 'DONE' or task['status'] == 'NA')):
            self.alm_update_task_status(alm_task, task['status'])

        return "Test ID %s" % alm_task.get_alm_id()


    def _alm_add_requirement(self, task, task_id):
        # HP Alm is very particular about JSON ordering - we must hand-craft it
        field_data = [
            ('type-id', self.issue_type),
            ('status', self.config['hp_alm_new_status']),
            ('name', task['title'].replace(':', '-')),
            ('description', self.sde_get_task_content(task)),
            ('req-priority', self.translate_priority(task['priority']))
        ]
        json_data = """%s""" % self._build_json_args(field_data, 'requirement')

        try:
            result = self._call_reqs_api(json_data, self.alm_plugin.URLRequest.POST)
        except APIError, err:
            raise AlmException('Unable to add task to HP Alm %s because of %s' %
                               (task['id'], err))

        logger.debug('Task %s added to HP Alm Project', task['id'])

        alm_task = HPAlmTask(task_id,
                             result['fields']['id'][0],
                             result['fields']['status'][0],
                             result['fields']['last-modified'][0],
                             self.config['hp_alm_done_statuses'])

        if (self.config['alm_standard_workflow'] and (task['status'] == 'DONE' or task['status'] == 'NA')):
            self.alm_update_task_status(alm_task, task['status'])

        return "Req ID %s" % alm_task.get_alm_id()

    def _add_requirement_coverage_to_test(self, test, requirement_id):
        field_data = [
            ('requirement-id', requirement_id),
            ('status', self.config['hp_alm_test_status']),
            ('entity-name', 'Test'),
            ('test-id', '1'),
            ('entity-type', 'test'),
            ('coverage-mode', 'All Configurations')
        ]
        json_data = """%s""" % self._build_json_args(field_data, 'requirement-coverage')

        try:
            self._call_api('%s/requirement-coverages' % self.project_uri,
                           method=self.alm_plugin.URLRequest.POST,
                           query_args=json_data)
        except APIError, error:
            raise AlmException('Unable to set requirement coverage for test plan: %s' % error)

    def alm_update_task_status(self, task, status):
        if not task or not self.config['alm_standard_workflow']:
            logger.debug('Status synchronization disabled')
            return

        if status == 'DONE' or status == 'NA':
            field_data = [('status', json.dumps(self.config['hp_alm_close_status']))]
        elif status == 'TODO':
            field_data = [('status', json.dumps(self.config['hp_alm_reopen_status']))]
        else:
            raise AlmException('Unexpected status %s: valid values are DONE, NA, or TODO' % status)

        field_data.append(('id', task.get_alm_id()))
        json_data = """{"entities": %s}""" % self._build_json_args(field_data)

        try:
            result = self._call_reqs_api(json_data, self.alm_plugin.URLRequest.PUT)
        except APIError, err:
            raise AlmException('Unable to update task status to %s '
                               'for requirement: '
                               '%s in HP Alm because of %s' %
                               (status, task.get_alm_id(), err))

        logger.debug('Status changed to %s for task %s in HP Alm', status, task.get_alm_id())

    def alm_disconnect(self):
        try:
            self._call_api('authentication-point/logout')
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


    def validate_configurations(self):
        try:
            req_types = self._call_api('%s/customization/entities/requirement/types/' % self.project_uri)
        except APIError, err:
            raise AlmException('Unable to retrieve requirement types: %s' % (err))
        for req_type in req_types['types']:
            if req_type['name'] == self.config['hp_alm_issue_type']:
                self.issue_type = req_type['id']
                return

        raise AlmException('Requirement type %s not found in project' % (self.config['hp_alm_issue_type']))


    def _fetch_test_plan_folder_id(self, query_args="{}"):
        try:
            result = self._call_api('%s/test-folders?query=%s&fields=id,name' % (self.project_uri,
                                                                               self._hp_query_encoder(query_args)))
        except APIError, error:
            raise AlmException('Failed to retrieve test plan folders: %s' % error)

        if result['TotalResults'] > 0:
            return result['entities'][0]['fields']['id'][0]
        else:
            return None

    def _get_top_test_folder_id(self):
        folder_id = self._fetch_test_plan_folder_id("{parent-id['0']}")

        if not folder_id:
            raise AlmException('Could not find the topmost folder in Test Plan')
        else:
            return folder_id

    def _create_test_plan_folder(self):
        json_data = self._build_json_args({
            "name": self.config['hp_alm_test_plan_folder'],
            "parent-id": self._get_top_test_folder_id()
        }, "test-folder")

        try:
            result = self._call_api('%s/test-folders' % self.project_uri, json_data, self.alm_plugin.URLRequest.POST)
        except APIError, error:
            raise AlmException('Unable to create a test plan folder: %s' % error)

        return result['fields']['id'][0]

    @staticmethod
    def _build_json_args(field_data=None, entity_type=None):
        args = []

        if field_data:
            fields_values = []
            for key, value in field_data:
                if type(value) is not ListType:
                    value = [value]

                values = [dict(value=v) for v in value]
                fields_values.append('{"Name": %s, "values": %s}' % (json.dumps(key), json.dumps(values)))
            args.append('"Fields": [%s]' % ','.join(fields_values))
        #if entity_type:
        #       args.append('"Type": %s' % json.dumps(entity_type))

        return '{%s}' % ','.join(args)

    def _hp_query_encoder(self, query):
        new_query = []

        for section in query.split(' '):
            if section == '':
                new_query.append('%20')
            else:
                new_query.append(urlencode_str(section))
        return '%20'.join(new_query)