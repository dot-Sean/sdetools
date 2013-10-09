import os

from urllib2 import HTTPError
from xmlrpclib import Fault

from sdetools.alm_integration.tests.alm_response_generator import AlmResponseGenerator


class TracResponseGenerator(AlmResponseGenerator):
    STATUS_NAMES = ['new', 'closed']
    ACTIONS = ['resolve', 'reopen']

    def __init__(self):
        initial_task_status = self.STATUS_NAMES[0]
        test_dir = os.path.dirname(os.path.abspath(__file__)) 
        super(TracResponseGenerator, self).__init__(initial_task_status, test_dir)

        self.rest_api_targets = {
            'system\.getAPIVersion': 'get_api_version',
            'ticket\.get$': 'get_ticket_by_id',
            'ticket\.query': 'query_ticket',
            'ticket\.create': 'create_ticket',
            'ticket\.update': 'update_ticket',
            'ticket\.getActions': 'get_ticket_actions',
        }

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

        return super(TracResponseGenerator, self).get_response(target, flags, data, None)

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
                task_number = data[0]
                task = self.get_alm_task(task_number)

                if task:
                    return self.generate_task(task['status'], task_number, task.get('milestone'))

            self.raise_error('405')
        else:
            self.raise_error('401')

    def query_ticket(self, target, flag, data, method):
        if not flag:
            if data:
                task_id = data[0]
                task_number = self.extract_task_number_from_title(task_id)
                response = []

                if self.get_alm_task(task_number):
                    response.append(task_number)

                return response

            self.raise_error('405')
        else:
            self.raise_error('401')

    def create_ticket(self, target, flag, data, method):
        if not flag:
            if data:
                task_title = data[0]
                task_number = self.extract_task_number_from_title(task_title)
                alm_task = self.get_alm_task(task_number)

                if not alm_task:
                    task_attributes = data[2]
                    task_status = task_attributes['status']
                    self.add_alm_task(task_number, task_title, task_status)

                    return task_number

            self.raise_error('405')
        else:
            self.raise_error('401')

    def update_ticket(self, target, flag, data, method):
        if not flag:
            if data:
                task_number = data[0]
                update_args = data[2]
                task = self.get_alm_task(task_number)

                if task:
                    milestone = update_args.get('milestone')
                    action = update_args.get('action')

                    if update_args.get('milestone'):
                        self.update_alm_task(task_number, 'milestone', milestone)
                    if action:
                        new_status = None

                        if action == self.ACTIONS[0]:
                            new_status = self.STATUS_NAMES[1]
                        elif action == self.ACTIONS[1]:
                            new_status = self.STATUS_NAMES[0]
                        self.update_alm_task(task_number, 'status', new_status)

                    task = self.get_alm_task(task_number)
                    return self.generate_task(task['status'], task_number, task.get('milestone'))
                else:
                    self.raise_error('405')
        else:
            self.raise_error('401')

    def get_ticket_actions(self, target, flag, data, method):
        if not flag:
            if data:
                task_number = data[0]
                action_set = []
                if self.get_alm_task(task_number):
                    for transition in self.ACTIONS:
                        action_set.append([transition, 'Label', 'Hints', ['Name', 'Value']])

                return action_set
            else:
                self.raise_error('405')
        else:
            self.raise_error('401')

    @staticmethod
    def generate_task(task_status, task_id, task_milestone):
        task_attrs = {
            "status": task_status,
            "changetime": '2013-10-02T20:27:27Z',
            "milestone": task_milestone
        }

        return [task_id, '2013-10-02T20:27:27Z', '2013-10-02T20:27:27Z', task_attrs]
