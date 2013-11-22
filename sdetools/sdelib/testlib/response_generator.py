import os
import json
import re
import urllib

from types import IntType
from mock import MagicMock
from urllib2 import HTTPError
from urlparse import urlparse
from datetime import datetime
from sdetools.extlib.defusedxml import minidom
from sdetools.sdelib.commons import get_directory_of_current_module


class ResponseGenerator(object):
    def __init__(self, rest_api_targets, resource_templates, test_dir=None, base_path='/'):
        """Initializes commonly used variables.

        Keyword arguments:
        rest_api_targets    -- Dict object containing key-value pairs used in get_response to triage API calls
                               to its corresponding response generating method.
                               Expected format:
                                 "regex_pattern_of_api_target": "method_to_call_on_match"
        resource_templates  -- List of resources we want to store. Specify the filename of the resource template.
        test_dir            -- Directory containing current test; used to locate response files
        base_path           -- URL that will be prepended to each rest api target.
                               Expected format:
                                 "/BASE_PATH/"

        """
        if test_dir is None:
            test_dir = get_directory_of_current_module(self)

        self.resources = {}
        self.test_dir = test_dir
        self.base_path = base_path
        self.alm_tasks = {}
        self.rest_api_targets = rest_api_targets

        for resource in resource_templates:
            resource_name, file_type = resource.split('.')
            self.resources[resource_name] = {
                'resources': {},
                'file_type': file_type
            }

        self.init_with_resources()

    def init_with_resources(self):
        pass

    @staticmethod
    def encode_response(result):
        """Convert response into a string."""
        if result is not None:
            return json.dumps(result)
        else:
            return "{}"

    @staticmethod
    def decode_data(data):
        """Convert request data into a python object."""
        try:
            return json.loads(data)
        except:
            return data

    def get_response(self, target, flags, data, method, headers=None):
        """Triage get_response calls to the correct response generator method based on the specified target.
        Response generator methods must accept the following parameters: [target, flag, data, method]

        Keyword Arguments:
        target  -- the API endpoint (without server information)
        flags   -- dict object containing response modifier flags in the form of
                  {response_func_name: keyword}.
        data    -- data passed along with the API call
        method  -- HTTP Verb, specified by the URLRequest class
        headers -- Values in the request header

        """
        self.target = target
        data = self.decode_data(data)
        print 'Generating %s response for target: %s' % (method, target)
        #print 'With flags: %s\n With data: ' % flags
        #print data

        for api_target in self.rest_api_targets:
            if re.match('%s%s' % (self.base_path, api_target), target):
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

    """
        Resource management functions
    """
    def generator_add_resource(self, resource_type, _id=None, resource_data={}):
        """Save a resource created through our mock.

        Keyword Arguments:
        resource_type -- One of the resources in self.resources
        _id           -- Unique identifier for the resource.
        resource_data -- Data to be stored. Usually from the data field in the post request
        """
        self._check_resource_exists(resource_type)
        if _id is None:
            _id = len(self.resources[resource_type]['resources'])
        if type(_id) == IntType:
            _id = str(_id)
        if _id not in self.resources[resource_type]['resources']:
            self.resources[resource_type]['resources'][_id] = resource_data

        return _id

    def generator_resource_exists(self, resource_type, _id):
        self._check_resource_exists(resource_type)

        return _id in self.resources[resource_type]['resources']

    def generator_get_resource(self, resource_type, _id, data_only=False):
        self._check_resource_exists(resource_type)
        if self.generator_resource_exists(resource_type, _id):
            task_data = self.resources[resource_type]['resources'][_id]

            if data_only:
                return task_data
            else:
                return self.generate_resource_from_template(resource_type, task_data)
        else:
            return None

    def generator_get_all_resource(self, resource_type):
        self._check_resource_exists(resource_type)
        resource_data = self.resources[resource_type]['resources'].values()

        return [self.generate_resource_from_template(resource_type, t) for t in resource_data]

    def generator_get_filtered_resource(self, resource_type, _filter):
        self._check_resource_exists(resource_type)
        filtered_tasks = []

        for resource_data in self.resources[resource_type]['resources'].values():
            if self._resource_in_scope(resource_data, _filter):
                filtered_tasks.append(self.generate_resource_from_template(resource_type, resource_data))

        return filtered_tasks

    @staticmethod
    def _resource_in_scope(task, _filter):
        for key, value in _filter.items():
            _task_value = task.get(key)
            if type(_task_value) == IntType:
                _task_value = str(_task_value)
            if _task_value is None or _task_value != value:
                return False
        return True

    def generator_update_resource(self, resource_type, _id, update_args):
        self._check_resource_exists(resource_type)
        if self.generator_resource_exists(resource_type, _id):
            resource = self.resources[resource_type]['resources'][_id]
            for key, value in update_args.items():
                resource[key] = value
        else:
            raise Exception('Resource does not exist: Type: %s, ID: %s' % (resource_type, _id))

    def generator_clear_resources(self, full_clear=False):
        for resource_type in self.resources.values():
            resource_type['resources'] = {}

        if not full_clear:
            self.init_with_resources()

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

    def _check_resource_exists(self, resource_type):
        if resource_type not in self.resources:
            self.raise_error('500', 'Invalid resource type %s' % resource_type)

    """
        Generator Functions
    """
    def generate_resource_from_template(self, resource_type, resource_data):
        self._check_resource_exists(resource_type)
        file_type = self.resources[resource_type]['file_type']

        if file_type == 'json':
            template = self.get_json_from_file(resource_type)
        elif file_type == 'xml':
            template = self.get_xml_from_file(resource_type)
        else:
            raise Exception('Unsupported file type %s' % file_type)

        for key, value in resource_data.items():
            template[key] = value

        return template