from urllib2 import HTTPError
from xmlrpclib import Fault

from sdetools.sdelib.testlib.response_generator import ResponseGenerator


class TracResponseGenerator(ResponseGenerator):
    ACTIONS = {
        'resolve': 'closed',
        'reopen': 'new'
    }

    def __init__(self, config=None, test_dir=None):
        resource_templates = ['ticket.xml']
        rest_api_targets = {
            'system\.getAPIVersion': 'get_api_version',
            'ticket\.get$': 'get_ticket_by_id',
            'ticket\.query': 'query_ticket',
            'ticket\.create': 'create_ticket',
            'ticket\.update': 'update_ticket',
            'ticket\.getActions': 'get_ticket_actions',
        }
        super(TracResponseGenerator, self).__init__(rest_api_targets, resource_templates, test_dir)

    @staticmethod
    def decode_data(data):
        return data

    @staticmethod
    def encode_response(response):
        return response

    def raise_error(self, error_code, return_value=None):
        try:
            super(TracResponseGenerator, self).raise_error(error_code, return_value)
        except HTTPError as err:
            raise Fault(err.code, err.msg)

    def get_proxy_response(self, args):
        target = args[0]
        flags = args[1]
        data = None

        if len(args) > 2:
            data = args[2:]

        success_code, response = super(TracResponseGenerator, self).get_response(target, flags, data, None)

        return response

    """
        Response functions
    """
    def get_api_version(self, target, flag, data, method):
        if not flag:
            return [0, 1, 0]
        else:
            self.raise_error('404')

    def get_ticket_by_id(self, target, flag, data, method):
        if not flag:
            if data:
                return self.generator_get_resource('ticket', data[0])
            self.raise_error('405')
        else:
            self.raise_error('401')

    def query_ticket(self, target, flag, data, method):
        if not flag:
            if data:
                task_number = self.extract_task_number_from_title(data[0])
                task = self.generator_get_resource('ticket', task_number)

                if task:
                    return task
                return []

            self.raise_error('405')
        else:
            self.raise_error('401')

    def create_ticket(self, target, flag, data, method):
        if not flag:
            if data:
                task_title = data[0]
                task_number = self.extract_task_number_from_title(task_title)

                if not self.generator_resource_exists('ticket', task_number):
                    self.generator_add_resource('ticket', task_number, {
                        'id': task_number,
                        'title': task_title,
                        'milestone': None,
                        'status': data[2]['status']
                    })
                    return task_number

            self.raise_error('405')
        else:
            self.raise_error('401')

    def update_ticket(self, target, flag, data, method):
        if not flag:
            if data:
                task_number = data[0]
                update_args = data[2]

                if self.generator_resource_exists('ticket', task_number):
                    milestone = update_args.get('milestone')
                    action = update_args.get('action')
                    update_values = {}

                    if milestone:
                        update_values['milestone'] = milestone
                    if action:
                        new_status = self.ACTIONS.get(action)
                        if new_status:
                            update_values['status'] = new_status
                    if update_values:
                        self.generator_update_resource('ticket', task_number, update_values)

                    return self.generator_get_resource('ticket', task_number)
                else:
                    self.raise_error('405')
        else:
            self.raise_error('401')

    def get_ticket_actions(self, target, flag, data, method):
        if not flag:
            if data:
                task_number = data[0]
                action_set = []
                if self.generator_resource_exists('ticket', task_number):
                    for transition in self.ACTIONS:
                        action_set.append([transition, 'Label', 'Hints', ['Name', 'Value']])

                return action_set
            else:
                self.raise_error('405')
        else:
            self.raise_error('401')

    def generate_resource_from_template(self, resource_type, resource_data):
        self._check_resource_type_exists(resource_type)
        task_attrs = {
            "status": resource_data['status'],
            "changetime": '2013-10-02T20:27:27Z',
            "milestone": resource_data['milestone']
        }

        return [resource_data['id'], '2013-10-02T20:27:27Z', '2013-10-02T20:27:27Z', task_attrs]
