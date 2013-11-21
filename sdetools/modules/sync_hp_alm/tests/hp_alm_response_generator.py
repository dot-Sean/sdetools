import json
import re

from cookielib import Cookie
from sdetools.sdelib.commons import urlencode_str
from sdetools.sdelib.testlib.response_generator import ResponseGenerator


class HPAlmResponseGenerator(ResponseGenerator):
    REQUIREMENT_TYPES = ['Undefined', 'Functional', 'Business', 'Folder', 'Testing', 'Group']
    TEST_TYPES = ["MANUAL"]

    def __init__(self, config, test_dir=None):
        hp_alm_domain = urlencode_str(config['hp_alm_domain'])
        hp_alm_project = urlencode_str(config['alm_project'])
        self.hp_alm_user = urlencode_str(config['alm_user'])
        statuses = ['Not Completed', 'Passed']
        base_path = 'qcbin'
        project_uri = '/%s/rest/domains/%s/projects/%s' % (base_path, hp_alm_domain, hp_alm_project)
        rest_api_targets = {
            '/%s/authentication-point/authenticate' % base_path: 'authenticate',
            '%s/requirements' % project_uri: 'call_requirements',
            '%s/customization/users/%s' % (project_uri, self.hp_alm_user): 'get_user',
            '%s/customization/entities/requirement/types/' % project_uri: 'get_requirement_types',
            '%s/customization/entities/test/types/' % project_uri: 'get_test_types',
            '%s/customization/used-lists\?name=Status' % project_uri: 'get_status_types',
            '%s/test-folders' % project_uri: 'call_test_folders',
            '%s/tests' % project_uri: 'call_tests',
            '/%s/authentication-point/logout' % base_path: 'logout',
            '%s/requirement\-coverages' % project_uri: 'call_requirement_coverage'
        }

        self.test_folders = [{'name': 'Subject', 'parent-id': '0', 'id': '1'}]
        self.tests = []
        self.requirements = []
        self.requirement_coverages = []
        super(HPAlmResponseGenerator, self).__init__(rest_api_targets, statuses, test_dir)

    """
       Response functions 
    """
    def call_requirement_coverage(self, target, flag, data, method):
        if not flag:
            if method == 'GET':
                response = self.generate_collection_entity()
                queries, fields = self.get_url_parameters(target)
                coverages = self.get_entities('requirement-coverage', queries, fields)

                if coverages:
                    response['TotalResults'] = len(coverages)
                    response['entities'] = coverages
                return response
            elif method == 'POST':
                if not self.is_data_valid(data, ['test-id', 'requirement-id']):
                    self.raise_error('405')

                query = [['test-id', data.get('test-id')], ['requirement-id', data.get('requirement-id')]]
                if not self.get_entities('requirement-coverage', query, ['requirement-id']):
                    self.requirement_coverages.append(data)
                    response = self.generate_entity('requirement-coverage')
                    for key, value in data.items():
                        response['Fields'].append(self.generate_requirement_field(key, value))
                    return response
                else:
                    self.raise_error('405', 'Duplicate requirement-coverage')
        else:
            self.raise_error('401')

    def call_tests(self, target, flag, data, method):
        if not flag:
            if method == 'GET':
                response = self.generate_collection_entity()
                queries, fields = self.get_url_parameters(target)
                tests = self.get_entities('test', queries, fields)

                if tests:
                    response['TotalResults'] = len(tests)
                    response['entities'] = tests

                return response
            elif method == 'POST':
                response = self.generate_entity('test')
                task_number = self.extract_task_number_from_title(data['name'].replace('-', ':'))
                data['id'] = task_number
                data['exec-status'] = self.statuses[0]
                data['last-modified'] = self.get_current_timestamp()
                self.tests.append(data)
                for key, value in data.items():
                    response['Fields'].append(self.generate_requirement_field(key, value))
                return response
            else:
                self.raise_error('403')
        else:
            self.raise_error('401')

    def call_test_folders(self, target, flag, data, method):
        if not flag:
            if method == 'GET':
                response = self.generate_collection_entity()
                queries, fields = self.get_url_parameters(target)
                folders = self.get_entities('test-folder', queries, fields)

                if folders:
                    response['TotalResults'] = len(folders)
                    response['entities'] = folders

                return response
            elif method == 'POST':
                valid_parent_id = False
                for folder in self.test_folders:
                    if not valid_parent_id and folder['id'] == data['parent-id']:
                        valid_parent_id = True
                    if folder['name'] == data['name']:
                        self.raise_error('500')
                if not valid_parent_id:
                    self.raise_error('405')

                data['id'] = len(self.test_folders) + 1
                self.test_folders.append(data)
                response = {"Fields": [], 'Type': 'test-folder'}
                for key, value in data.items():
                    response['Fields'].append(self.generate_requirement_field(key, value))

                return response
        else:
            self.raise_error('401')

    def authenticate(self, target, flag, data, method):
        if not flag:
            c = Cookie(None, 'LWSSO_COOKIE_KEY', 'cookieValue', '80', '80', 'www.foo.bar', None, None, '/',
                       None, False, False, 'TestCookie', None, None, None)

            return c
        else:
            self.raise_error('401')

    def get_requirements(self, target, flag, data):
        queries, fields = self.get_url_parameters(target)
        response = self.generate_collection_entity()
        reqs = self.get_entities('requirement', queries, fields)

        if reqs:
            response['TotalResults'] = len(reqs)
            response['entities'] = reqs

        return response

    def post_requirements(self, flag, data):
        if not flag:
            response = self.generate_entity('requirement')

            if self.get_entities('requirement', [['name', data['name']]], []):
                self.raise_error('405')

            task_number = self.extract_task_number_from_title(data['name'].replace('-', ':'))
            data['id'] = task_number
            data['status'] = self.statuses[0]
            data['last-modified'] = self.get_current_timestamp()
            self.requirements.append(data)
            for key, value in data.items():
                response['Fields'].append(self.generate_requirement_field(key, value))
            return response
        else:
            self.raise_error('500')

    def update_requirement_status(self, flag, data):
        if not data['id'] or not data['status']:
            self.raise_error('405')
        if self.update_entity('requirement', [['id', data['id']]], {'status': data['status']}):
            return ''
        else:
            self.raise_error('405')

    def call_requirements(self, target, flag, data, method):
        if not flag:
            if method == 'GET':
                return self.get_requirements(target, flag, data)
            elif method == 'POST':
                return self.post_requirements(flag, data)
            elif method == 'PUT':
                return self.update_requirement_status(flag, data)
            self.raise_error('405')
        else:
            self.raise_error('401')

    def get_user(self, target, flag, data, method):
        if not flag:
            user = self.get_json_from_file('user')
            user['Name'] = self.hp_alm_user

            return user
        else:
            self.raise_error('401')

    def get_requirement_types(self, target, flag, data, method):
        if not flag:
            response = {'types': self.generate_task_types(self.REQUIREMENT_TYPES)}

            return response
        else:
            self.raise_error('401')

    def get_test_types(self, target, flag, data, method):
        if not flag:
            response = {'types': self.generate_task_types(self.TEST_TYPES)}

            return response
        else:
            self.raise_error('401')

    def get_status_types(self, target, flag, data, method):
        if not flag:
            return {
                'lists': [
                    {
                        'Items': [
                            {'value': 'Not Completed'},
                            {'value': 'Not Run'},
                            {'value': 'Failed'},
                            {'value': 'Blocker'},
                            {'value': 'Passed'}
                        ]
                    }
                ]
            }
        else:
            self.raise_error('401')

    def logout(self, target, flag, data, method):
        if not flag:
            return ''
        else:
            self.raise_error('500')

    # Response helpers
    @staticmethod
    def decode_data(data):
        try:
            data = json.loads(data)
            data_fields = {}

            for field in data['Fields']:
                data_fields[field['Name']] = field['values'][0]['value']

            return data_fields
        except:
            return data

    def update_entity(self, type, queries, update):
        return self.get_entities(type, queries, [], update)[0]

    def get_entities(self, _type, queries, fields, update={}):
        if _type == 'test':
            entity_list = self.tests
        elif _type == 'test-folder':
            entity_list = self.test_folders
        elif _type == 'requirement-coverage':
            entity_list = self.requirement_coverages
        else:
            entity_list = self.requirements
        entities = []

        for entity in entity_list:
            for param, value in queries:
                if not re.match(value, entity.get(param)):
                    found = False
                    break
                else:
                    found = True
            if found:
                if update:
                    for key, value in update.items():
                        entity[key] = value

                _entity = self.generate_entity(_type)
                for param in fields:
                    _entity['Fields'].append(self.generate_requirement_field(param, entity[param]))
                entities.append(_entity)

        return entities

    def get_url_parameters(self, url):
        query, fields = [q[0] for q in super(HPAlmResponseGenerator, self).get_url_parameters(url).values()]
        queries = [re.findall('[-\w ]+', q) for q in query.split(';')]
        fields = fields.split(',')

        return queries, fields

    @staticmethod
    def encode_response(result):
        """ Convert response into a string """
        if result:
            return json.dumps(result)
        else:
            return ""

    # Generate JSON
    @staticmethod
    def generate_task_types(task_types):
        types = []

        for i in range (0, len(task_types)):
            types.append({
                    'name': task_types[i],
                    'id': i
                })

        return types

    @staticmethod
    def generate_requirement_field(name, value):
        return {
            "Name": name,
            "values": [
                {
                    "value": value
                }
            ]
        }

    def generate_task_fields(self, task):
        response = {
            "Fields": [
                self.generate_requirement_field('id', task['id']),
                self.generate_requirement_field('status', task['status']),
                self.generate_requirement_field('last-modified', task['timestamp'])
            ]
        }
        return response

    @staticmethod
    def generate_collection_entity():
        return {
            "TotalResults": 0,
            "entities": []
        }

    @staticmethod
    def generate_entity(type):
        return {
            "Fields": [],
            "Type": type
        }