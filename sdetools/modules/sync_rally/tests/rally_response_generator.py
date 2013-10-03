import os
import sys
import re

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))))
from sdetools.alm_integration.tests.alm_response_generator import AlmResponseGenerator


class RallyResponseGenerator(AlmResponseGenerator):
    API_VERSION = '1.39'
    STATUS_NAMES = ['Defined', 'Completed', 'Accepted']

    def __init__(self, host, protocol='http'):
        initial_task_status = self.STATUS_NAMES[0]
        test_dir = os.path.dirname(os.path.abspath(__file__)) 
        super(RallyResponseGenerator, self).__init__(initial_task_status, test_dir)

        base_path = 'slm/webservice/%s' % self.API_VERSION
        self.api_url = '%s://%s/%s' % (protocol, host, base_path)
        self.rest_api_targets = {
            'task\.js': 'get_tasks',
            'subscription\.js': 'get_subscription',
            'project\.js': 'get_project',
            'hierarchicalrequirement\.js': 'get_requirements',
            'hierarchicalrequirement/[0-9]+\.js': 'call_card',
            'hierarchicalrequirement/create\.js': 'create_card'
        }

    """
       Response functions 
    """
    def get_tasks(self, target, flag, data, method):
        if not flag:
            return self.get_json_from_file('task')
        else:
            self.raise_error('401')

    def get_subscription(self, target, flag, data, method):
        if not flag:
            return self.get_json_from_file('subscription')
        else:
            self.raise_error('401')

    def get_project(self, target, flag, data, method):
        if not flag:
            return self.get_json_from_file('project')
        else:
            self.raise_error('401')

    def get_requirements(self, target, flag, data, method):
        if not flag:
            task_name = data['query']
            task_number = self.get_task_number_from_title(task_name)
            task = self.get_alm_task(task_number)
            requirements = self.get_json_from_file('hierarchical_requirements')

            if task:
                result = requirements['QueryResult']['Results'][0]
                new_ref = re.sub('[0-9]+(?=\.js)', task_number, result['_ref'])
                result['_ref'] = new_ref
                result['_refObjectName'] = task['name']
            else:
                requirements['QueryResult']['TotalResultCount'] = 0
                requirements['QueryResult']['Results'] = []

            return requirements
        else:
            self.raise_error('401')

    def call_card(self, target, flag, data, method):
        if not flag:
            task_number = re.search('[0-9]+(?=\.js$)', target).group(0)
            task = self.get_alm_task(task_number)

            if not task:
                self.raise_error('405')
            if method == 'GET':
                card = self.get_json_from_file('card')
                card_data = card['HierarchicalRequirement']
                card_data['FormattedID'] = task_number
                new_ref = re.sub('[0-9]+(?=\.js$)', task_number, card_data['_ref'])
                card_data['_ref'] = new_ref
                card_data['ScheduleState'] = task['status']
                card_data['_refObjectName'] = task['name']
                card_data['Name'] = task['name']

                return card
            elif method == 'POST':
                new_status = data['HierarchicalRequirement']['ScheduleState']
                self.update_alm_task(task_number, 'status', new_status)

                return None
        else:
            self.raise_error('404')

    def create_card(self, target, flag, data, method):
        if not flag:
            create_args = data['HierarchicalRequirement']
            task_number = self.get_task_number_from_title(create_args['Name'])
            task = self.get_alm_task(task_number)

            if not task:
                self.add_alm_task(task_number, create_args['Name'])
                return self.get_json_from_file('create_result')
            else:
                self.raise_error('405')
        else:
            self.raise_error('401')