import json
import re
import urllib
from urlparse import urlparse

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
            'authentication-point/logout': 'logout'
        }

        self.test_folders = [{'name': 'Subject', 'parent-id': '0', 'id': '1'}]

        super(HPAlmResponseGenerator, self).__init__(rest_api_targets, statuses, test_dir)

    """
       Response functions 
    """
    def call_test_folders(self, target, flag, data, method):
        if not flag:
            if method == 'GET':
                response = {
                    "TotalResults": 0,
                    "entities": []
                }
                query, fields = [q.split('=')[1] for q in urlparse(urllib.unquote(target)).query.split('&')]
                queries = [re.findall('[-\w ]+', q) for q in query.split(';')]
                fields = fields.split(',')

                for folder in self.test_folders:
                    for param, value in queries:
                        if folder[param] != value:
                            found = False
                            break
                        else:
                            found = True
                    if found:
                        response['TotalResults'] = 1
                        entity = {'Fields': []}
                        for param in fields:
                            entity['Fields'].append(self.generate_requirement_field(param, folder[param]))
                        response['entities'] = [entity]
                        break
                print response
                return response
            elif method == 'POST':
                data_fields = self.read_data_fields(data)
                valid_parent_id = False
                for folder in self.test_folders:
                    if not valid_parent_id and folder['id'] == data_fields['parent-id']:
                        valid_parent_id = True
                    if folder['name'] == data_fields['name']:
                        self.raise_error('500')
                if not valid_parent_id:
                    self.raise_error('405')

                data_fields['id'] = len(self.test_folders) + 1
                self.test_folders.append(data_fields)
                response = {"Fields": []}
                for key, value in data_fields.items():
                    response['Fields'].append(self.generate_requirement_field(key, value))

                return response
        else:
            self.raise_error('401')

    def authenticate(self, target, flag, data, method):
        if not flag:
            c = Cookie(None, 'LWSSO_COOKIE_KEY', 'cookieValue', '80', '80', 'www.foo.bar', None, None, '/',
                       None, False, False, 'TestCookie', None, None, None)
            response = {
                "cookiejar": c
            }

            return response
        else:
            self.raise_error('401')

    def get_requirements(self, flag, data):
        query = data['query']
        fields = data['fields'].split(',')
        task_number = self.extract_task_number_from_title(query)
        task = self.generator_get_task(task_number)
        response = {
            "TotalResults": 0,
            "entities": []
        }

        if task:
            entity = self.generate_task_fields(task)
            response['TotalResults'] = 1
            response['entities'] = [entity]

        return json.dumps(response)

    def post_requirements(self, flag, data):
        fields = data['Fields']

        for field in fields:
            if field['Name'] == 'status':
                status = field['values'][0]['value']
            elif field['Name'] == 'name':
                name = field['values'][0]['value']

        if not status or not name:
            self.raise_error('405')

        task_number = self.extract_task_number_from_title(name)
        task = self.generator_get_task(task_number)

        if not task:
            self.generator_add_task(task_number, name, status)
            new_task = self.generator_get_task(task_number)
            response = self.generate_task_fields(new_task)

            return json.dumps(response)
        else:
            self.raise_error('500')

    def update_requirement_status(self, flag, data):
        fields = data['entities'][0]['Fields']

        for field in fields:
            if field['Name'] == 'status':
                status = field['values'][0]['value']
            elif field['Name'] == 'id':
                task_number = field['values'][0]['value']

        if not task_number or not status:
            self.raise_error('405')

        task = self.generator_get_task(task_number)

        if task:
            self.generator_update_task(task_number, 'status', status)
        else:
            self.raise_error('404')

    def call_requirements(self, target, flag, data, method):
        if not flag:
            if data:
                if method == 'GET':
                    return self.get_requirements(flag, data)
                elif method == 'POST':
                    data = json.loads(data)
                    return self.post_requirements(flag, data)
                elif method == 'PUT':
                    data = json.loads(data)
                    return self.update_requirement_status(flag, data)
            self.raise_error('405')
        else:
            self.raise_error('401')

    def get_user(self, target, flag, data, method):
        if not flag:
            user = self.get_json_from_file('user')
            user['Name'] = self.hp_alm_user

            return json.dumps(user)
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
            return ""
        else:
            self.raise_error('500')

    """
        Generate JSON
    """
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
        return  {
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
    def read_data_fields(data):
        data_fields = {}
        for field in data['Fields']:
            data_fields[field['Name']] = field['values'][0]['value']

        return data_fields