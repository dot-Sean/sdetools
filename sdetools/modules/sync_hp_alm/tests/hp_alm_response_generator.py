import json

from cookielib import Cookie
from sdetools.sdelib.commons import urlencode_str
from sdetools.sdelib.testlib.response_generator import ResponseGenerator


class HPAlmResponseGenerator(ResponseGenerator):
    ISSUE_TYPES = ['Undefined', 'Functional', 'Business', 'Folder', 'Testing', 'Group']

    def __init__(self, config, test_dir=None):
        hp_alm_domain = urlencode_str(config['hp_alm_domain'])
        hp_alm_project = urlencode_str(config['alm_project'])
        self.hp_alm_user = urlencode_str(config['alm_user'])
        statuses = ['Not Completed', 'Passed']
        rest_api_targets = {
            'authentication-point/authenticate': 'authenticate',
            'rest/domains/%s/projects/%s/requirements' % (hp_alm_domain, hp_alm_project): 'call_requirements',
            'rest/domains/%s/projects/%s/customization/users/%s' % (hp_alm_domain, hp_alm_project, self.hp_alm_user):
                'get_user',
            'rest/domains/%s/projects/%s/customization/entities/requirement/types/' % (hp_alm_domain, hp_alm_project):
                'get_requirement_types',
            'authentication-point/logout': 'logout'
        }
        super(HPAlmResponseGenerator, self).__init__(rest_api_targets, statuses, test_dir)

    """
       Response functions 
    """
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

        return response

    def post_requirements(self, flag, data):
        print data
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

            return response
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

            return user
        else:
            self.raise_error('401')

    def get_requirement_types(self, target, flag, data, method):
        if not flag:
            response = {}
            response['types'] = self.generate_requirement_types()

            return response
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
    def generate_requirement_types(self):
        types = []

        for i in range (0, len(self.ISSUE_TYPES)):
            types.append({
                    'name': self.ISSUE_TYPES[i],
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
