import os
import json
import re

from mock import MagicMock
from urllib2 import HTTPError
from datetime import datetime
from sdetools.extlib.defusedxml import minidom
from sdetools.sdelib.commons import abc, get_directory_of_current_module
abstractmethod = abc.abstractmethod


class ResponseGenerator(object):
    def __init__(self, rest_api_targets, statuses, test_dir=None):
        """
            Initializes commonly used variables.

            statuses            - List of valid task statuses. First entry will be used as the default status
            test_dir            - Directory containing current test; used to locate response files
            alm_tasks           - Stores tasks created through our mock
            rest_api_targets    - Dict object containing key-value pairs used in get_response to triage API calls
                                  to its corresponding response generating method.
                                  Expected format:
                                    "regex_pattern_of_api_target": "method_to_call_on_match"
        """
        if test_dir is None:
            test_dir = get_directory_of_current_module(self)

        self.statuses = statuses
        self.test_dir = test_dir
        self.alm_tasks = {}
        self.rest_api_targets = rest_api_targets
        self.init_with_tasks()

    def init_with_tasks(self):
        pass

    def get_response(self, target, flags, data, method):
        """
            Triage get_response calls to the correct response generator method based on the specified target.
            Response generator methods must accept the following parameters: [target, flag, data, method]

            Keywords:
            target - the path of the API call (without host name)
            flags  - dict object containing response modifier flags in the form of
                     {target: keyword}.
            data   - data passed along with the API call
            method - HTTP Verb, specified by the URLRequest class
        """
        for api_target in self.rest_api_targets:
            if re.match(api_target, target):
                func_name = self.rest_api_targets.get(api_target)

                if func_name is not None:
                    func = getattr(self, func_name)

                    if callable(func):
                        return func(target, flags.get(func_name), data, method)

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

    def generator_get_valid_statuses(self):
        return self.statuses

    """
        Task management functions
    """
    def generator_add_task(self, task_number, task_name=None, status=None):
        """
            Save a task created through our mock. Uses the task number
            as the alm_id
        """
        if not self.alm_tasks.get(task_number):
            if not task_name:
                task_name = "T%s" % task_number
            if status is None:
                status = self.generator_get_valid_statuses()[0]
            self.alm_tasks[task_number] = {
                "name": task_name,
                "id": task_number,
                "status": status,
                "timestamp": self.get_current_timestamp()
            }

    def generator_get_task(self, task_number):
        return self.alm_tasks.get(task_number)

    def generator_get_all_tasks(self):
        return self.alm_tasks

    def generator_update_task(self, task_number, field, value):
        if self.alm_tasks.get(task_number):
            self.alm_tasks[task_number][field] = value

    def generator_clear_tasks(self, full_clear=False):
        self.alm_tasks = {}

        if not full_clear:
            self.init_with_tasks()

    """
        Response reader functions
    """
    def _read_response_file(self, file_name):
        file_path = os.path.join(self.test_dir, 'response', file_name)

        f = open(file_path)
        response = f.read()
        f.close()

        return response

    def get_json_from_file(self, file_name):
        raw_json = self._read_response_file('%s.json' % file_name)
        return json.loads(raw_json)

    def get_xml_from_file(self, file_name):
        raw_xml = self._read_response_file('%s.xml' % file_name)
        return minidom.parseString(raw_xml)

    """
        Util functions
    """
    @staticmethod
    def extract_task_number_from_title(s):
        task_number = re.search("(?<=T)[0-9]+((?=[:'])|$)", s)

        if task_number:
            return task_number.group(0)
        else:
            return None

    @staticmethod
    def get_current_timestamp():
        return datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")

    @staticmethod
    def is_data_valid(data, fields=[]):
        if data is None:
            return False
        for field in fields:
            if not field in data:
                return False

        return True
