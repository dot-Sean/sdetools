import re
import os
import sys
import random

from urllib2 import HTTPError
from mock import MagicMock

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))))
from sdetools.alm_integration.tests.alm_response_generator import AlmResponseGenerator
from sdetools.sdelib.commons import urlencode_str


class PivotalTrackerResponseGenerator(AlmResponseGenerator):
    PROJECT_ID = '1000'
    STATUS_NAMES = ['unstarted', 'accepted']
    REST_API_TARGETS = {
        'me': 'get_user',
        'projects': 'get_projects',
        '%project_uri/stories\?filter="(.*):"&fields=current_state,name,updated_at,id': 'get_stories',
        '%project_uri/stories\?filter=type:release,(.*)&fields=id': 'get_release_marker',
        '%project_uri/epics\?filter=(.*)&fields=id': 'get_epic',
        '%project_uri/epics': 'add_epic',
        '%project_uri/stories': 'add_story',
        '%project_uri/stories/[0-9]*': 'update_status'
    }

    def __init__(self, project_name, release_marker_name, epic_name):
        initial_task_status = self.STATUS_NAMES[0]
        test_dir = os.path.dirname(os.path.abspath(__file__)) 
        super(PivotalTrackerResponseGenerator, self).__init__(initial_task_status, test_dir)

        self.project_uri = 'projects/%s' % self.PROJECT_ID
        self.project_name = project_name
        self.release_marker_name = release_marker_name
        self.epic_name = epic_name
        self.epics = {}

    def get_response(self, target, flag, data, method):
        for api_target in self.REST_API_TARGETS:
            match_target = re.sub('%project_uri', self.project_uri, api_target)
            if re.match(match_target, target):
                func_name = self.REST_API_TARGETS.get(api_target)
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

    """
       Response functions 
    """
    def get_user(self, target, flag, data, method):
        if not flag:
            user_info = self.get_json_from_file('me')
            user_info['projects'][0]['project_id'] = self.PROJECT_ID
            user_info['projects'][0]['id'] = self.PROJECT_ID

            return user_info
        else:
            self.raise_error('401')

    def get_projects(self, target, flag, data, method):
        if not flag:
            project = self.get_json_from_file('project')
            project['name'] = self.project_name
            project['id'] = int(self.PROJECT_ID)

            return [project]
        else:
            self.raise_error('401')

    def get_stories(self, target, flag, data, method):
        if not flag:
            stories = []
            story_id = re.search('(?<=(filter="T)).*(?=:)', target).group(0)
            task = self.get_alm_task(story_id)

            if task:
                story = self.get_json_from_file('story')
                story['name'] = task['name']
                story['id'] = story_id
                story['current_state'] = task['status']
                stories.append(story)

            return stories
        else:
            self.raise_error('401')

    def get_release_marker(self, target, flag, data, method):
        if not flag:
            release_markers = []
            release_marker_name = re.search('(?<=type:release,).*(?=&fields)', target).group(0)

            if release_marker_name == urlencode_str(self.release_marker_name):
                release_marker = self.get_json_from_file('release_marker')
                release_markers.append(release_marker)

            return release_markers
        else:
            self.raise_error('401')

    def get_epic(self, target, flag, data, method):
        if not flag:
            epics = []
            epic_name = re.search('(?<=filter=).*(?=&fields)', target).group(0)
            epic = self.epics.get(epic_name)

            if epic:
                _epic = self.get_json_from_file('epic')
                _epic['name'] = epic['name']
                _epic['label']['name'] = epic['label']
                _epic['id'] = epic['id']
                _epic['project_id'] = self.PROJECT_ID
                epics.append(_epic)

            return epics
        else:
            self.raise_error('401')

    def add_epic(self, target, flag, data, method):
        if not flag and data:
            epic_key = urlencode_str(data['name'])

            if not self.epics.get(epic_key):
                epic = {
                    "name": data['name'],
                    "label": data['label']['name'],
                    "id": random.randint(1, 999999999)
                }
                self.epics[epic_key] = epic  # Use encoded string as key for easy access
                epic_response = self.get_json_from_file('epic')
                epic_response['name'] = epic['name']
                epic_response['label']['name'] = epic['label']
                epic_response['id'] = epic['id']
                epic_response['project_id'] = self.PROJECT_ID

                return epic_response
            else:
                self.raise_error('500', 'Epic %s already exists!' % data['name'])
        else:
            self.raise_error('401')

    def add_story(self, target, flag, data, method):
        if not flag and data:
            story_id = self.get_task_number_from_title(data['name'])
            task = self.get_alm_task(story_id)
            if not task:
                self.add_alm_task(story_id, data['name'], data['current_state'])
                response = self.get_json_from_file('post_story')
                response['project_id'] = self.PROJECT_ID
                response['current_state'] = data['current_state']
                response['name'] = data['name']
                response['id'] = story_id

                return response
            else:
                self.raise_error('500', 'Story %s already exists!' % data['name'])
        else:
            self.raise_error('401')

    def update_status(self, target, flag, data, method):
        if not flag and data:
            story_id = re.search('(?<=stories/)[0-9]+', target).group(0)
            self.update_alm_task(story_id, 'status', data['current_state'])

            response = self.get_json_from_file('post_story')

            return response
        else:
            self.raise_error('401')
