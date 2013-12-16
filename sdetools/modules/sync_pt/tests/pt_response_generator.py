import re
import random

from sdetools.sdelib.testlib.response_generator import ResponseGenerator
from sdetools.sdelib.commons import urlencode_str


class PivotalTrackerResponseGenerator(ResponseGenerator):
    def __init__(self, config, test_dir=None):
        base_path = '/services/v5/'
        resource_templates = ['story.json', 'epic.json', 'me.json', 'project.json']
        self.project_id = 1000
        self.project_uri = 'projects/%s' % self.project_id
        self.project_name = config['alm_project']
        self.release_marker_name = config['alm_project_version']
        rest_api_targets = {
            'me': 'get_user',
            'projects$': 'get_projects',
            '%s/stories\?filter=type:release,(.*)&fields=id' % self.project_uri: 'get_release_marker',
            '%s/stories\?filter=.*' % self.project_uri: 'get_stories',
            '%s/epics\?filter=(.*)&fields=id' % self.project_uri: 'get_epic',
            '%s/epics$' % self.project_uri: 'add_epic',
            '%s/stories$' % self.project_uri: 'add_story',
            '%s/stories/[0-9]*' % self.project_uri: 'update_status'
        }
        super(PivotalTrackerResponseGenerator, self).__init__(rest_api_targets, resource_templates, test_dir, base_path)

    def init_with_resources(self):
        self.generator_add_resource('me', self.project_id, {
            'projects': [{
                'project_id': self.project_id,
                'id': self.project_id
            }]
        })
        self.generator_add_resource('project', self.project_id, {
            'name': self.project_name,
            'id': int(self.project_id)
        })
        if self.release_marker_name:
            self.generator_add_resource('story', '9999999990', {
                'id': '9999999990',
                'story_type': 'release',
                'name': self.release_marker_name
            })

    """
       Response functions 
    """
    def get_user(self, target, flag, data, method):
        if not flag:
            return self.generator_get_resource('me', self.project_id)
        else:
            self.raise_error('401')

    def get_projects(self, target, flag, data, method):
        if not flag:
            return self.generator_get_all_resource('project')
        else:
            self.raise_error('401')

    def get_stories(self, target, flag, data, method):
        if not flag:
            stories = []
            params = self.get_url_parameters(target)
            if not params.get('filter'):
                self.raise_error('400')

            story_id = re.search('(?<=T)[0-9]+(?=:)', params['filter'][0]).group(0)

            return self.generator_get_filtered_resource('story', {'id': story_id})
        else:
            self.raise_error('401')

    def get_release_marker(self, target, flag, data, method):
        if not flag:
            release_marker_name = re.search('(?<=type:release,).*(?=&fields)', target).group(0)

            return self.generator_get_filtered_resource('story', {'story_type': 'release', 'name': release_marker_name})
        else:
            self.raise_error('401')

    def get_epic(self, target, flag, data, method):
        if not flag:
            epic_name = re.search('(?<=filter=).*(?=&fields)', target).group(0)

            return self.generator_get_filtered_resource('epic', {'name': epic_name})
        else:
            self.raise_error('401')

    def add_epic(self, target, flag, data, method):
        if not flag and data:
            epic_name = urlencode_str(data['name'])

            if len(self.generator_get_filtered_resource('epic', {'name': epic_name})) == 0:
                resource_data = data
                resource_data['project_id'] = self.project_id
                resource_data['id'] = random.randint(1, 999999999)
                self.generator_add_resource('epic', resource_data['id'], resource_data)

                return self.generate_resource_from_template('epic', resource_data)
            else:
                self.raise_error('500', 'Epic %s already exists!' % data['name'])
        else:
            self.raise_error('401')

    def add_story(self, target, flag, data, method):
        if not flag and data:
            story_id = self.extract_task_number_from_title(data['name'])

            if self.generator_get_resource('story', story_id) is None:
                if data['story_type'] == 'feature' and data['current_state'] != 'unscheduled' and data.get('estimate') is None:
                    self.raise_error('400', 'Expected an estimate')
                data['id'] = story_id
                data['project_id'] = self.project_id
                self.generator_add_resource('story', story_id, data)

                return self.generate_resource_from_template('story', data)
            else:
                self.raise_error('500', 'Story %s already exists!' % data['name'])
        else:
            self.raise_error('401')

    def update_status(self, target, flag, data, method):
        if not flag and data:
            story_id = re.search('(?<=stories/)[0-9]+', target).group(0)
            task = self.generator_get_resource('story', story_id)

            if task:
                if data['current_state'] != 'unscheduled' and task['story_type'] == 'feature' and \
                        task.get('estimate') is None and data.get('estimate') is None:
                    self.raise_error('400', 'Expected an estimate')

                self.generator_update_resource('story', story_id, {'current_state': data['current_state']})
                task['current'] = data['current_state']

                return task
            self.raise_error('404')
        else:
            self.raise_error('401')
