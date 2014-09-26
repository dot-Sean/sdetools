# Copyright SDElements Inc
# Extensible two way integration with HP Alm
import re

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

    def parse_response(self, result, headers):
        if not result or result.strip() == "":
            return {}
        else:
            parsed_response = json.loads(result)

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
        """ Simplify the entity fields collection to make it easier to access field values """
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

    def __init__(self, task_id, alm_id, status, last_modified, done_statuses, alm_task_type):
        self.task_id = task_id
        self.alm_id = alm_id
        self.timestamp = last_modified
        self.status = status
        self.done_statuses = done_statuses  # comma-separated list
        self.alm_task_type = alm_task_type

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

    def get_alm_task_type(self):
        return self.alm_task_type


class HPAlmConnector(AlmConnector):
    """Connects SD Elements to HP Alm"""
    alm_name = 'HP Alm'

    def __init__(self, config, alm_plugin):
        super(HPAlmConnector, self).__init__(config, alm_plugin)

        """ Adds HP Alm specific config options to the config file"""
        config.opts.add('hp_alm_issue_type', 'IDs for issues raised in HP Alm',
                                 default='Functional')
        config.opts.add('hp_alm_new_status', 'status to set for new tasks in HP Alm',
                                 default='Not Completed')
        config.opts.add('hp_alm_reopen_status', 'status to set to reopen a task in HP Alm',
                                 default='Not Completed')
        config.opts.add('hp_alm_close_status', 'status to set to close a task in HP Alm',
                                 default='Passed')
        config.opts.add('hp_alm_done_statuses', 'Statuses that signify a task is Done in HP Alm',
                                 default='Passed')
        config.opts.add('hp_alm_domain', 'Domain',
                                 default=None)
        config.opts.add('hp_alm_test_plan_folder', 'Test plan folder where we import our test tasks',
                                 default='SD Elements')
        config.opts.add('hp_alm_test_type', 'Default type for new test plans',
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
        self.test_plan_folder_id = None
        self.hp_alm_test_type_id = None
        #We will map requirements its associated tests based on the problem id
        self.requirement_to_test_mapping = {}

    def prune_tasks(self, tasks):
        """ We want to organize the tasks in a way such that we sync all non-test tasks first,
        then sync the test tasks. This allows us to create requirement coverages when we sync the
        test tasks.
        """
        if 'testing' in self.config['alm_phases']:
            # Extract non-testing in-scope tasks
            dev_tasks = [task for task in tasks if self.in_scope(task) and task['phase'] != 'testing']

            # Extract those task's weakness IDs.
            weakness_ids = set(t['weakness']['id'] for t in dev_tasks)

            # Update our requirements to tests mapping
            for weakness_id in weakness_ids:
                self.requirement_to_test_mapping[weakness_id] = []

            # Extract corresponding test tasks.
            test_tasks = [t for t in tasks if t['phase'] == 'testing' and t['weakness']['id'] in weakness_ids]

            return dev_tasks + test_tasks
        else:
            return super(HPAlmConnector, self).prune_tasks(tasks)

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

    def _call_api_collection(self, collection, query_args, method=URLRequest.GET):
        try:
            result = self._call_api('%s/%s' % (self.project_uri, collection), query_args, method)
        except APIError, err:
            raise AlmException('Unable to %s %s entity from HP Alm. Reason: %s' % (method, collection, str(err)))

        if not result or (result.get('TotalResults') == 0):
            return None
        else:
            return result

    def alm_connect_project(self):
        # Connect to the project
        try:
            user = self._call_api('%s/customization/users/%s' % (self.project_uri, urlencode_str(self.config['alm_user'])))
        except APIError, err:
            raise AlmException('Unable to verify domain and project details: %s' % (err))

        if user['Name'] != self.config['alm_user']:
            raise AlmException('Unable to verify user access to domain and project')

    def alm_validate_configurations(self):
        # Check requirement type
        self.issue_type = self._validate_entity_type('requirement', self.config['hp_alm_issue_type'])

        # Check test plan type
        self.hp_alm_test_type_id = self._validate_entity_type('test', self.config['hp_alm_test_type'])

        # Check statuses
        try:
            requirement_lists = self._call_api('%s/customization/used-lists?name=Status' % self.project_uri)
        except APIError, err:
            raise AlmException('Unable to retrieve statuses: %s' % err)

        requirement_statuses = [item['value'] for item in requirement_lists['lists'][0]['Items']]

        for config in ['hp_alm_new_status', 'hp_alm_reopen_status', 'hp_alm_close_status']:
            status = self.config[config]

            if not status in requirement_statuses:
                raise AlmException('Invalid %s: %s. Expected one of %s' % (config, status, requirement_statuses))

        difference_set = set(self.config['hp_alm_done_statuses']).difference(requirement_statuses)
        if difference_set:
            raise AlmException('Invalid hp_alm_done_statuses: %s. Expected one of %s' %
                               (difference_set, requirement_statuses))

    def alm_get_task(self, task):
        task_id = self._extract_task_id(task['id'])

        if not task_id:
            return None
        query_args = {
            'query': "{name['%s-*']}" % task_id,
            'fields': 'id,name,last-modified'
        }

        if task['phase'] != 'testing':
            return self._alm_call_requirement(task_id, query_args, task)
        else:
            return self._alm_get_test_plan(task_id, query_args, task)

    def _alm_get_test_plan(self, task_id, query_args, task):
        query_args['fields'] += ',exec-status'
        result = self._call_api_collection('tests', query_args)
        req_ids = self.requirement_to_test_mapping.get(task['weakness']['id'])

        if result is None:
            # Check if an associated requirement is there.
            # We only add a new test task if it has no related task(s) in sde, or the related task(s) is in scope.
            # Otherwise we will just sync the status
            if req_ids is not None and len(req_ids) == 0:
                self.ignored_tasks.append(task['id'])
            return None
        else:
            field_data = result['entities'][0]['fields']

            if req_ids:
                self._add_requirement_coverage(field_data['id'][0], field_data['name'][0], req_ids)

            return HPAlmTask(task_id,
                             field_data['id'][0],
                             field_data['exec-status'][0],
                             field_data['last-modified'][0],
                             self.config['hp_alm_done_statuses'],
                             result['entities'][0]['type'])

    def _alm_call_requirement(self, task_id, query_args, task, method=URLRequest.GET):
        if method == URLRequest.GET:
            query_args['fields'] += ',status,req-priority'
        else:
            query_args.extend([
                ('type-id', self.issue_type),
                ('status', self.config['hp_alm_new_status']),
                ('req-priority', self.translate_priority(task['priority']))
            ])
            query_args = self._build_json_args(query_args, 'requirement')
        result = self._call_api_collection('requirements', query_args, method)

        if result is None:
            return None
        if result.get('entities'):
            result = result['entities'][0]
        if self.requirement_to_test_mapping:
            self.requirement_to_test_mapping[task['weakness']['id']].append(result['fields']['id'][0])

        return HPAlmTask(task_id,
                         result['fields']['id'][0],
                         result['fields']['status'][0],
                         result['fields']['last-modified'][0],
                         self.config['hp_alm_done_statuses'],
                         result['type'])

    def _alm_add_test_plan(self, task_id, field_data, task):
        if self.test_plan_folder_id is None:
            _query = "{name['%s']}" % self.config['hp_alm_test_plan_folder']
            self.test_plan_folder_id = self._fetch_test_plan_folder_id(_query) or self._create_test_plan_folder()

        field_data.extend([
            ('parent-id', self.test_plan_folder_id),
            ('subtype-id', self.hp_alm_test_type_id),
            ('owner', self.config['alm_user']),
            ('status', 'Imported')
        ])
        json_data = self._build_json_args(field_data, 'test')
        result = self._call_api_collection('tests', json_data, URLRequest.POST)
        req_ids = self.requirement_to_test_mapping.get(task['weakness']['id'])

        if req_ids:
            self._add_requirement_coverage(result['fields']['id'][0], result['fields']['name'][0], req_ids)

        return HPAlmTask(task_id,
                         result['fields']['id'][0],
                         result['fields']['exec-status'][0],
                         result['fields']['last-modified'][0],
                         self.config['hp_alm_done_statuses'],
                         result['type'])

    def alm_add_task(self, task):
        task_id = self._extract_task_id(task['id'])

        if not task_id:
            return None

        field_data = [
            ('name', self._hp_convert_test_title(task['title'])),
            ('description', self.sde_get_task_content(task))
        ]

        if task['phase'] != "testing":
            task_type = 'Requirement'
            alm_task = self._alm_call_requirement(task_id, field_data, task, URLRequest.POST)
        else:
            task_type = 'Test'
            alm_task = self._alm_add_test_plan(task_id, field_data, task)

        logger.debug('Task %s added to HP Alm Project', task['id'])

        if self.config['alm_standard_workflow'] and (task['status'] == 'DONE' or task['status'] == 'NA'):
            self.alm_update_task_status(alm_task, task['status'])

        return "HP Alm %s ID: %s" % (task_type, alm_task.get_alm_id())

    def _get_uncovered_requirements(self, test_id, req_ids):
        query_args = {
            'query': "{test-id[%s]}" % test_id,
            'fields': 'requirement-id'
        }
        coverages = self._call_api_collection('requirement-coverages', query_args)

        if coverages and req_ids:
            covered_req_ids = [c['fields']['requirement-id'][0] for c in coverages['entities']]
            req_ids = [r for r in req_ids if r not in covered_req_ids]
        return req_ids

    def _add_requirement_coverage(self, test_id, test_name, req_ids):
        for req_id in self._get_uncovered_requirements(test_id, req_ids):
            json_data = self._build_json_args([
                ('requirement-id', req_id),
                ('entity-name', test_name),
                ('test-id', test_id),
                ('entity-type', 'test'),
                ('coverage-mode', 'All Configurations')
            ], 'requirement-coverage')

            self._call_api_collection('requirement-coverages', json_data, URLRequest.POST)

            logger.info('Added test %s as a requirement coverage for %s' % (test_id, req_id))

    def alm_update_task_status(self, task, status):
        if not task or not self.config['alm_standard_workflow']:
            logger.debug('Status synchronization disabled')
            return

        if task.get_alm_task_type() == 'test':
            logger.debug("Status synchronization disabled for test plans")
            return

        if status == 'DONE' or status == 'NA':
            field_data = [('status', self.config['hp_alm_close_status'])]
        elif status == 'TODO':
            field_data = [('status', self.config['hp_alm_reopen_status'])]
        else:
            raise AlmException('Unexpected status %s: valid values are DONE, NA, or TODO' % status)

        field_data.append(('id', task.get_alm_id()))
        json_data = """%s""" % self._build_json_args(field_data, 'requirement')

        try:
            self._call_api('%s/requirements' % self.project_uri, json_data, self.alm_plugin.URLRequest.PUT)
        except APIError, err:
            raise AlmException('Unable to update task status to %s for requirement: %s in HP Alm because of %s' %
                               (status, task.get_alm_id(), err))

        logger.debug('Status changed to %s for task %s in HP Alm', status, task.get_alm_id())

    def alm_disconnect(self):
        try:
            self._call_api('authentication-point/logout')
        except APIError, err:
            raise AlmException('Unable to logout from HP Alm. Reason: %s' % (str(err)))

    def convert_markdown_to_alm(self, content, ref):
        return '<html>'+self.mark_down_converter.convert(content)+'</html>'

    def _validate_entity_type(self, type, check_value):
        try:
            entity_types = self._call_api('%s/customization/entities/%s/types/' % (self.project_uri, type))
        except APIError, err:
            raise AlmException('Unable to retrieve %s types: %s' % (type, err))
        for entity_type in entity_types['types']:
            if entity_type['name'] == check_value:
                return entity_type['id']
        raise AlmException('%s type %s not found in project' % (type.capitalize(), check_value))

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
        json_data = self._build_json_args([
            ("name", self.config['hp_alm_test_plan_folder']),
            ("parent-id", self._get_top_test_folder_id())
        ], "test-folder")

        return self._call_api_collection('test-folders', json_data, URLRequest.POST)['fields']['id'][0]

    @staticmethod
    def _build_json_args(field_data=None, entity_type=None):
        # HP Alm is very particular about JSON ordering - we must craft it in a specific way
        args = []

        if field_data:
            fields_values = []
            for key, value in field_data:
                if type(value) is not ListType:
                    value = [value]

                values = [dict(value=v) for v in value]
                fields_values.append('{"Name": %s, "values": %s}' % (json.dumps(key), json.dumps(values)))
            args.append('"Fields": [%s]' % ','.join(fields_values))
        if entity_type:
            args.append('"Type": %s' % json.dumps(entity_type))

        return '{%s}' % ','.join(args)

    @staticmethod
    def _hp_convert_test_title(title):
        """Converts the title of a test task in SDE to conform to HP Alm's syntax restrictions:
        A test name cannot include the following characters: \ / : " ? < > | * % '
        """
        title = re.sub(r'[\/\\\|]', r' ', title)
        title = re.sub(r'[<>\*\?\%]', r'', title)
        title = re.sub(r'[\'\"]', r'`', title)

        return title.replace(':', '-')

    @staticmethod
    def _hp_query_encoder(query):
        return urlencode_str(query).replace('+', '%20')
