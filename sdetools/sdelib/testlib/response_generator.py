import os
import json
import re
import urllib

from mock import MagicMock
from urllib2 import HTTPError
from urlparse import urlparse
from datetime import datetime
from sdetools.extlib.defusedxml import minidom
from sdetools.sdelib.commons import abc, get_directory_of_current_module
from sdetools.sdelib import log_mgr
abstractmethod = abc.abstractmethod
logger = log_mgr.mods.add_mod(__name__)


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

    @staticmethod
    def encode_response(result):
        """ Convert response into a string """
        if result is not None:
            return json.dumps(result)
        else:
            return "{}"

    @staticmethod
    def decode_data(data):
        """ Convert request data into a python object """
        try:
            return json.loads(data)
        except:
            # Return the original data
            return data

    def get_response(self, target, flags, data, method, headers=None):
        """
            Triage get_response calls to the correct response generator method based on the specified target.
            Response generator methods must accept the following parameters: [target, flag, data, method]

            Keywords:
            target - the path of the API call (without host name)
            flags  - dict object containing response modifier flags in the form of
                     {response_func_name: keyword}.
            data   - data passed along with the API call
            method - HTTP Verb, specified by the URLRequest class
        """
        self.target = target
        data = self.decode_data(data)
        print 'Generating %s response for target: %s' % (method, target)
        #print 'With flags: %s\n With data: ' % flags
        #print data

        for api_target in self.rest_api_targets:
            if re.match(api_target, target):
                func_name = self.rest_api_targets.get(api_target)

                if func_name is not None:
                    func = getattr(self, func_name)

                    if callable(func):
                        response = func(target, flags.get(func_name), data, method)
                        try:
                            response = self.encode_response(response)
                        except:
                            # Do not encode the response
                            pass
                        return 200, response

                self.raise_error('500', 'Response generator error: Could not find method %s' % func_name)
        self.raise_error('404')

    def raise_error(self, error_code, message=None):
        fp_mock = MagicMock()

        if message is None:
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
        else:
            message
        message = json.dumps(message)
        fp_mock.read.return_value = message

        raise HTTPError('%s' % self.target, error_code, message, '', fp_mock)

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
        task_number = re.search("(?<=T)[0-9]+", s)

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

    @staticmethod
    def get_url_parameters(url):
        return dict([q.split('=') for q in urlparse(urllib.unquote_plus(url)).query.split('&') if q])

