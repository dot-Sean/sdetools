import os
import json
import re

from mock import MagicMock
from urllib2 import HTTPError
from sdetools.extlib.defusedxml import minidom
from sdetools.sdelib.commons import abc
abstractmethod = abc.abstractmethod


class AlmResponseGenerator(object):
    def __init__(self, initial_task_status, test_dir):
        self.initial_task_status = initial_task_status
        self.test_dir = test_dir
        self.alm_tasks = {}
        """
            rest_api_targets should contain key-value pairs in the following format:
                "regex_pattern_of_api_target": "method_to_call_on_match"
        """
        self.rest_api_targets = {}

    def get_response(self, target, flag, data, method):
        for api_target in self.rest_api_targets:
            if re.match(api_target, target):
                func_name = self.rest_api_targets.get(api_target)
                func = getattr(self, func_name)

                if callable(func):
                    return func(target, flag.get(func_name), data, method)
                else:
                    self.raise_error('500', 'Response generator error: Could not find method %s' % func_name)

        self.raise_error('404')

    def raise_error(self, error_code, return_value=None):
        fp_mock = MagicMock()

        if error_code == '400':
            message = 'Invalid parameters'
        elif error_code == '403':
            message = 'No permission'
        elif error_code == '404':
            message = 'Not found'
        elif error_code == '500':
            message = 'Server error'
        else:
            message = 'Unknown error'

        if not return_value:
            fp_mock.read.return_value = message
        else:
            fp_mock.read.return_value = return_value

        raise HTTPError('', error_code, message, '', fp_mock)

    def add_alm_task(self, task_number, task_name=None, status=None):
        """
            Save task using the task number as the id
        """
        if not self.alm_tasks.get(task_number):
            if not task_name:
                task_name = "T%s" % task_number
            if not status:
                status = self.initial_task_status

            self.alm_tasks[task_number] = {


                "name": task_name,
                "id": task_number,


                "status": status
            }

    def get_alm_task(self, task_number):
        return self.alm_tasks.get(task_number)

    def update_alm_task(self, task_number, field, value):
        if self.alm_tasks.get(task_number):
            self.alm_tasks[task_number][field] = value

    def clear_alm_tasks(self):
        self.alm_tasks = {}

    def _read_response_file(self, file_name):
        file_path = os.path.join(self.test_dir, 'response', file_name)
        f = open(file_path)
        response = f.read()

        return response

    def get_json_from_file(self, file_name):
        raw_json = self._read_response_file('%s.json' % file_name)
        return json.loads(raw_json)

    def get_xml_from_file(self, file_name):
        raw_xml = self._read_response_file('%s.xml' % file_name)
        return minidom.parseString(raw_xml)

    def get_task_number_from_title(self, s):
        task_number = re.search("(?<=T)[0-9]+((?=[:'])|$)", s)

        if task_number:
            return  task_number.group(0)
        else:
            return None
