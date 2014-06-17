import os
import json
import re
import urllib

from types import IntType, DictionaryType, ListType
from mock import MagicMock
from urllib2 import HTTPError
from urlparse import urlparse, parse_qs
from datetime import datetime
from sdetools.extlib.defusedxml import minidom
from sdetools.sdelib.commons import get_directory_of_current_module

RESPONSE_HEADERS = [('Server', 'Mock')]


class ResponseGenerator(object):
    """Base response generator class, used in unittests"""

    def __init__(self, rest_api_targets, resource_templates, test_dir=None):
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

        self.target = None
        self.resources = {}
        self.test_dir = test_dir
        self.rest_api_targets = rest_api_targets

        for resource in resource_templates:
            resource_name, file_type = resource.split('.')
            self.resources[resource_name] = {
                'resources': {},
                'file_type': file_type
            }

        self.init_with_resources()

    def init_with_resources(self):
        """Initializes the response generator with these resources"""
        pass

    @staticmethod
    def encode_response(response):
        """Convert the response into a string"""
        if response is not None:
            return json.dumps(response)
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

        for api_target in self.rest_api_targets:
            if not re.match(api_target, target):
                continue

            func_name = self.rest_api_targets.get(api_target)
            if func_name is None:
                self.raise_error('500', 'Response generator error: No response method defined for target: %s' % api_target)

            func = getattr(self, func_name)
            if not callable(func):
                self.raise_error('500', 'Response generator error: Uncallable response method: %s' % func_name)

            headers, response = func(target, flags.get(func_name), data, method)
            try:
                response = self.encode_response(response)
            except:
                # Failed to encode the response, return raw data
                pass
            return 200, headers, response
        self.raise_error('404')

    def raise_error(self, error_code, message=None):
        """Basic error response generator"""
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
        message = json.dumps(message)
        fp_mock.read.return_value = message

        raise HTTPError('%s' % self.target, error_code, message, '', fp_mock)

    #
    #Resource management functions
    #
    def generator_add_resource(self, resource_type, _id=None, resource_data=None):
        """Save a resource created through our mock.

        Keyword Arguments:
        resource_type -- One of the resources in self.resources
        _id           -- Unique identifier for the resource.
        resource_data -- Data to be stored. Usually from the data field in the post request

        """
        self._check_resource_type_exists(resource_type)
        if _id is None:
            _id = len(self.resources[resource_type]['resources'])
        if type(_id) == IntType:
            _id = str(_id)
        if _id not in self.resources[resource_type]['resources']:
            if resource_data is None:
                resource_data = {}
            self.resources[resource_type]['resources'][_id] = resource_data

        return _id

    def generator_remove_resource(self, resource_type, _id):
        if _id in self.resources[resource_type]['resources']:
            self.resources[resource_type]['resources'].pop(_id)

    def generator_resource_exists(self, resource_type, _id):
        self._check_resource_type_exists(resource_type)
        if _id == IntType:
            _id = str(_id)

        return _id in self.resources[resource_type]['resources']

    def generator_get_resource(self, resource_type, _id, data_only=False):
        self._check_resource_type_exists(resource_type)
        if self.generator_resource_exists(resource_type, _id):
            task_data = self.resources[resource_type]['resources'][_id]

            if data_only:
                return task_data
            else:
                return self.generate_resource_from_template(resource_type, task_data)
        else:
            return None

    def generator_get_all_resource(self, resource_type):
        """Returns all resource of the given type"""
        self._check_resource_type_exists(resource_type)
        resource_data = self.resources[resource_type]['resources'].values()

        return [self.generate_resource_from_template(resource_type, t) for t in resource_data]

    def generator_get_filtered_resource(self, resource_type, _filter):
        """Returns a list of resource of the given resource_type filtered by
            values in the _filter dict
        """
        self._check_resource_type_exists(resource_type)
        filtered_tasks = []

        for resource_data in self.resources[resource_type]['resources'].values():
            if self._resource_in_scope(resource_data, _filter):
                filtered_tasks.append(self.generate_resource_from_template(resource_type, resource_data))

        return filtered_tasks

    @staticmethod
    def _resource_in_scope(task, _filter):
        """Determines if a resource is in scope by checking if the values in _filter match
            the corresponding values in the resource
        """
        for key, value in _filter.items():
            _task_value = task.get(key)
            if type(_task_value) == IntType:
                _task_value = str(_task_value)
            if type(value) == ListType:
                value = value[0]
            if _task_value is None or not re.match(value, _task_value):
                return False
        return True

    def generator_update_resource(self, resource_type, _id, update_args):
        if self.generator_resource_exists(resource_type, _id):
            resource = self.resources[resource_type]['resources'][_id]
            for key, value in update_args.items():
                resource[key] = value
        else:
            raise Exception('Resource does not exist: Type: %s, ID: %s' % (resource_type, _id))

    def generator_clear_resources(self, full_clear=False):
        """Removes all stored resources from the generator. If full_clear is true,
            do not re-initialize the default resources
        """
        for resource_type in self.resources.values():
            resource_type['resources'] = {}

        if not full_clear:
            self.init_with_resources()

    #
    #   Response reader functions
    #
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

    #
    #   Util functions
    #
    @staticmethod
    def extract_task_number_from_title(s):
        """Extracts the task number from a string containing the SDE task ID"""
        task_number = re.search("(?<=T)[0-9]+", s)

        if task_number:
            return task_number.group(0)
        else:
            return None

    @staticmethod
    def get_current_timestamp():
        return datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")

    @staticmethod
    def is_data_valid(data, fields=None):
        """Check if the data param of a URL request contains the fields in fields"""
        if not fields:
            return True
        if data is None:
            return False
        for field in fields:
            if not field in data:
                return False

        return True

    @staticmethod
    def get_url_parameters(url, quote_plus=True):
        """ Returns a dictionary containing the url parameters
            quote_plus : true if spaces in the url are encoded as '+', false if spaces are '%20'
        """
        if quote_plus:
            url = urllib.unquote_plus(url)
        else:
            url = urllib.unquote(url)

        return parse_qs(urlparse(url).query)

    def _check_resource_type_exists(self, resource_type):
        """Checks that the resource type is one of the defined types"""
        if resource_type not in self.resources:
            self.raise_error('500', 'Invalid resource type %s' % resource_type)

    #
    #   Generator Functions
    #
    def generate_resource_from_template(self, resource_type, resource_data):
        """Loads a json resource file corresponding to resource_type and update it with
            values from resource_data
        """
        self._check_resource_type_exists(resource_type)
        file_type = self.resources[resource_type]['file_type']

        if file_type == 'json':
            template = self.get_json_from_file(resource_type)
        elif file_type == 'xml':
            template = self.get_xml_from_file(resource_type)
        else:
            raise Exception('Unsupported file type %s' % file_type)

        for key, value in resource_data.items():
            if type(value) == DictionaryType:
                if key not in template:
                    template[key] = {}
                template[key] = self._update_template(template[key], value)
            else:
                template[key] = value

        return self._update_template(template, resource_data)

    def _update_template(self, template, data):
        """Update the fields and sub-fields of a json template"""
        for key, value in data.items():
            if type(value) == DictionaryType:
                if key not in template:
                    template[key] = {}
                template[key] = self._update_template(template[key], value)
            else:
                template[key] = value

        return template