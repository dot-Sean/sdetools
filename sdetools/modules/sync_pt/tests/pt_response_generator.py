import re
import random

from sdetools.sdelib.testlib.response_generator import ResponseGenerator
from sdetools.sdelib.commons import urlencode_str


class PivotalTrackerResponseGenerator(ResponseGenerator):
    def __init__(self, config, test_dir=None):
        base_path = 'services/v5'
        self.PROJECT_ID = 1000
        self.project_uri = '/%s/projects/%s' % (base_path, self.PROJECT_ID)
        self.project_name = config['alm_project']
        self.release_marker_name = config['alm_project_version']
        self.epic_name = config['pt_group_label']
        self.epics = {}
        statuses = ['unstarted', 'accepted']
        rest_api_targets = {
            '/%s/me' % base_path: 'get_user',
            '/%s/projects$' % base_path: 'get_projects',
            '%s/stories\?filter="(.*):"&fields=current_state,name,updated_at,id,estimate' % self.project_uri: 'get_stories',
            '%s/stories\?filter=type:release,(.*)&fields=id' % self.project_uri: 'get_release_marker',
            '%s/epics\?filter=(.*)&fields=id' % self.project_uri: 'get_epic',
            '%s/epics$' % self.project_uri: 'add_epic',
            '%s/stories$' % self.project_uri: 'add_story',
            '%s/stories/[0-9]*' % self.project_uri: 'update_status'
        }
        super(PivotalTrackerResponseGenerator, self).__init__(rest_api_targets, statuses, test_dir)

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
            params = self.get_url_parameters(target)
            if not params.get('filter'):
                self.raise_error('400')

            story_id = re.search('(?<=T)[0-9]+(?=:)', params['filter'][0]).group(0)
            task = self.generator_get_task(story_id)

            if task:
                story = self.get_json_from_file('story')
                story['name'] = task['name']
                story['id'] = story_id
                story['current_state'] = task['status']
                story['story_type'] = task['story_type']
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
            story_id = self.extract_task_number_from_title(data['name'])
            task = self.generator_get_task(story_id)

            if not task:
                if data['story_type'] == 'feature' and data['current_state'] == 'started' and data.get('estimate') is None:
                    self.raise_error('400', 'Expected an estimate')
                self.generator_add_task(story_id, data['name'], data['current_state'])
                self.generator_update_task(story_id, 'story_type', data['story_type'])
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
            task = self.generator_get_task(story_id)

            if task:
                if task['story_type'] == 'feature' and data.get('estimate') is None:
                    self.raise_error('400', 'Expected an estimate')

                self.generator_update_task(story_id, 'status', data['current_state'])
                response = self.get_json_from_file('post_story')

                return response
            self.raise_error('404')
        else:
            self.raise_error('401')
