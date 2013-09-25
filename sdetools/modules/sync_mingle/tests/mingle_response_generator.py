import re, os, sys
from urllib2 import HTTPError
from mock import MagicMock

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))))
from sdetools.alm_integration.tests.alm_response_generator import AlmResponseGenerator

class MingleResponseGenerator(AlmResponseGenerator):
    STATUS_NAMES = ['Ready for Analysis', 'closed']
    API_TARGETS = {'get_projects':'projects.xml',
                   'get_cards':'%s.xml',
                   'update_status':'%s/[0-9].*\.xml'
                   }
    BASE_PATH = 'api/v2'

    def __init__(self, host, project_name, project_version, username, protocol='http'):
        initial_task_status = self.STATUS_NAMES[0]
        test_dir = os.path.dirname(os.path.abspath(__file__)) 
        super(MingleResponseGenerator, self).__init__(initial_task_status, test_dir)
        self.project_uri = 'projects/%s/cards' %  self.urlencode_str(project_name)
        self.api_url = '%s://%s/%s' % (protocol, host, self.BASE_PATH)
        self.project_version = project_version
        self.username = username

    def get_response(self, target, flag, data, method):
        if target == self.API_TARGETS['get_projects']:
            return self.get_projects(flag)
        elif target == self.API_TARGETS['get_cards'] % self.project_uri:
            return self.get_cards(flag)
        elif re.match(self.API_TARGETS['update_status'] % (self.project_uri), target):
            return self.update_status(flag)
        elif self.API_TARGETS['get_task'] % self.project_uri in target:
            return self.get_task(flag, target)
        elif target == self.API_TARGETS['post_issue'] % self.project_uri:
            return self.post_issue(flag, data)
        elif re.match(self.API_TARGETS['update_status'] % self.project_uri, target):
            return self.update_status(flag, target, data)
        else:
            self.raise_error('404')

    def raise_error(self, error_code):
        fp_mock = MagicMock()
        if error_code == '401':
            fp_mock.read.return_value = '{"message":"Requires authentication","documentation_url":"http://developer.github.com/v3"}'
            raise HTTPError('%s' % self.api_url, '401', 'Unauthorized user', '', fp_mock)
        elif error_code == '404':
            fp_mock.read.return_value = '{"message":"Not found","documentation_url":"http://developer.github.com/v3"}'
            raise HTTPError('%s' % self.api_url, '404', 'Not found', '', fp_mock)


    """
       Response functions 
    """
    """
       JSON Generator 
    """
