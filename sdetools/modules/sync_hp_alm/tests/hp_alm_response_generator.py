import json
import re

from cookielib import Cookie
from sdetools.sdelib.commons import urlencode_str
from sdetools.sdelib.testlib.response_generator import ResponseGenerator


class HPAlmResponseGenerator(ResponseGenerator):
    REQUIREMENT_TYPES = ['Undefined', 'Functional', 'Business', 'Folder', 'Testing', 'Group']
    TEST_TYPES = ["MANUAL"]

    def __init__(self, config, test_dir=None):
        self.new_status = config['hp_alm_new_status']
        hp_alm_domain = urlencode_str(config['hp_alm_domain'])
        hp_alm_project = urlencode_str(config['alm_project'])
        self.hp_alm_user = config['alm_user']
        project_uri = 'rest/domains/%s/projects/%s' % (hp_alm_domain, hp_alm_project)
        resource_templates = ['user.json', 'requirement.json', 'test.json', 'test-folder.json', 'requirement-coverage.json']
        rest_api_targets = {
            'authentication-point/authenticate': 'authenticate',
            '%s/requirements' % project_uri: 'call_requirements',
            '%s/customization/users/%s' % (project_uri, urlencode_str(self.hp_alm_user)): 'get_user',
            '%s/customization/entities/requirement/types/' % project_uri: 'get_requirement_types',
            '%s/customization/entities/test/types/' % project_uri: 'get_test_types',
            '%s/customization/used-lists\?name=Status' % project_uri: 'get_status_types',
            '%s/test-folders' % project_uri: 'call_test_folders',
            '%s/tests' % project_uri: 'call_tests',
            'authentication-point/logout': 'logout',
            '%s/requirement\-coverages' % project_uri: 'call_requirement_coverage'
        }

        self.test_folders = [{'name': 'Subject', 'parent-id': '0', 'id': '1'}]
        self.tests = []
        self.requirements = []
        self.requirement_coverages = []
        super(HPAlmResponseGenerator, self).__init__(rest_api_targets, resource_templates, test_dir, '/qcbin/')

    def init_with_resources(self):
        self.generator_add_resource('user', resource_data={'Name': self.hp_alm_user})
        self.generator_add_resource('test-folder', resource_data={'name': 'Subject', 'parent-id': '0', 'id': '1'})

    """
       Response functions 
    """
    def call_requirement_coverage(self, target, flag, data, method):
        if not flag:
            if method == 'GET':
                query, fields = self.get_url_parameters(target)
                entities = self.generator_get_filtered_resource('requirement-coverage', query)

                return self.generate_collection_entity(entities)
            elif method == 'POST':
                if not self.is_data_valid(data, ['test-id', 'requirement-id']):
                    self.raise_error('405')

                query = {
                    'test-id': data.get('test-id'),
                    'requirement-id': data.get('requirement-id')
                }
                entities = self.generator_get_filtered_resource('requirement-coverage', query)

                if not entities:
                    self.generator_add_resource('requirement-coverage', resource_data=data)

                    return self.generate_resource_from_template('requirement-coverage', data)
                else:
                    self.raise_error('405', 'Duplicate requirement-coverage for test %s and requirement %s' %
                                     (data.get('test-id'), data.get('requirement-id')))
        else:
            self.raise_error('401')

    def call_tests(self, target, flag, data, method):
        if not flag:
            if method == 'GET':
                query, fields = self.get_url_parameters(target)

                return self.generate_collection_entity(self.generator_get_filtered_resource('test', query))
            elif method == 'POST':
                task_number = self.extract_task_number_from_title(data['name'].replace('-', ':'))
                data['id'] = task_number
                data['exec-status'] = self.new_status
                data['last-modified'] = self.get_current_timestamp()
                self.generator_add_resource('test', task_number, data)

                return self.generate_resource_from_template('test', data)
            else:
                self.raise_error('403')
        else:
            self.raise_error('401')

    def call_test_folders(self, target, flag, data, method):
        if not flag:
            if method == 'GET':
                queries, fields = self.get_url_parameters(target)
                entities = self.generator_get_filtered_resource('test-folder', queries)

                return self.generate_collection_entity(entities)
            elif method == 'POST':
                if self.is_data_valid(data, ['parent-id', 'name']):
                    if self.generator_get_filtered_resource('test-folder', {'name': data['name']}):
                        self.raise_error('405')

                    data['id'] = self.generator_add_resource('test-folder', resource_data=data)
                    self.generator_update_resource('test-folder', data['id'], data)

                    return self.generate_resource_from_template('test-folder', data)
                self.raise_error('405')
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
        entities = self.generator_get_filtered_resource('requirement', queries)

        return self.generate_collection_entity(entities)

    def post_requirements(self, flag, data):
        if not flag:
            task_number = self.extract_task_number_from_title(data['name'].replace('-', ':'))
            if self.generator_resource_exists('requirement', task_number):
                self.raise_error('405', 'Duplicate requirement')

            data['id'] = task_number
            data['last-modified'] = self.get_current_timestamp()

            self.generator_add_resource('requirement', task_number, resource_data=data)

            return self.generate_resource_from_template('requirement', data)
        else:
            self.raise_error('500')

    def update_requirement_status(self, flag, data):
        if not self.is_data_valid(data, ['id', 'status']):
            self.raise_error('405')

        self.generator_update_resource('requirement', data['id'], {'status': data['status']})

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
            return self.generator_get_all_resource('user')[0]
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

    def get_url_parameters(self, url):
        query, fields = [q[0] for q in super(HPAlmResponseGenerator, self).get_url_parameters(url).values()]
        queries = {}

        for q in query.split(';'):
            key, value = re.findall('[-\w ]+', q)
            if key == 'name':
                value = value.replace(':', '-')
            queries[key] = value
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

    def generate_resource_from_template(self, resource_type, resource_data):
        if resource_type in ['requirement', 'requirement-coverage', 'test', 'test-folder']:
            entity = {
                "Fields": [],
                "Type": resource_type
            }

            for key, value in resource_data.items():
                entity['Fields'].append(self.generate_requirement_field(key, value))

            return entity
        else:
            return super(HPAlmResponseGenerator, self).generate_resource_from_template(resource_type, resource_data)

    @staticmethod
    def generate_collection_entity(entities=[]):
        return {
            "TotalResults": len(entities),
            "entities": entities
        }
