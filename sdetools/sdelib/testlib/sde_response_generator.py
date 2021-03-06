import re
import random

from sdetools.sdelib.testlib.response_generator import ResponseGenerator, RESPONSE_HEADERS


class SdeResponseGenerator(ResponseGenerator):
    def __init__(self, config, test_dir=None):
        self.analysis_tools = ['appscan', 'appscan_enterprise', 'veracode', 'fortify', 'webinspect']
        self.default_project_id = 1296
        self.default_app_id = 874
        self.app_name = config['sde_application']
        self.project_name = config['sde_project']
        resource_templates = ['application.json', 'project.json', 'task.json', 'text_note.json', 'ide_note.json',
                              'analysis_note.json', 'project_analysis_note.json', 'phases.json', 'taskstatuses.json']
        rest_api_targets = {
            '/api/applications': 'call_applications',
            '/api/projects': 'get_projects',
            '/api/tasks/[0-9]+-[0-9a-zA-z]+': 'call_task',
            '/api/tasks\?': 'get_tasks',
            '/api/tasknotes.*': 'call_task_notes',
            '/api/projectnotes/analysis$': 'add_project_analysis_note',
            '/api/taskstatuses': 'get_taskstatuses',
            '/api/phases$': 'get_phases'
        }

        super(SdeResponseGenerator, self).__init__(rest_api_targets, resource_templates, test_dir)

    def init_with_resources(self):
        app_data = {'id': self.default_app_id, 'name': self.app_name}
        self.generator_add_resource('application', self.default_app_id, app_data)
        project_data = {'name': self.project_name, 'id': self.default_project_id, 'application': self.default_app_id}
        self.generator_add_resource('project', self.default_project_id, project_data)
        self.generator_add_resource('task', '40', self.get_json_from_file('T40'))
        self.generator_add_resource('task', '36', self.get_json_from_file('T36'))
        self.generator_add_resource('task', '38', self.get_json_from_file('T38'))
        self.generator_add_resource('phases', '', self.get_json_from_file('phases'))
        self.generator_add_resource('taskstatuses', '', self.get_json_from_file('taskstatuses'))

    def generate_sde_task(self, task_number=None, project_id=None, status=None, priority=7, phase='requirements',
                          tags=None, verification_status=None):
        if task_number is None:
            task_number = '%d' % random.randint(50, 999999999)
        if project_id is None:
            project_id = self.default_project_id
        if status is None:
            status = 'TODO'
        if tags is None:
            tags = []

        sde_task = {
            "title": "T%s: Task Title" % task_number,
            "timestamp": self.get_current_timestamp(),
            "priority": priority,
            "project": '%d' % project_id,
            "phase": phase,
            "status": status,
            "id": '%d-T%s' % (project_id, task_number),
            "tags": tags,
            "verification_status": verification_status
        }
        self.generator_add_resource('task', task_number, sde_task)

        return self.generate_resource_from_template('task', sde_task)

    """
       Response functions 
    """
    def get_phases(self, target, flag, data, method):
        if not flag:
            if method == 'GET':
                params = self.get_url_parameters(target)
                if params:
                    phases = self.generator_get_filtered_resource('phases', params)
                else:
                    phases = self.generator_get_all_resource('phases')
                return RESPONSE_HEADERS, phases[0]
            else:
                self.raise_error('400')
        else:
            self.raise_error('401')

    def get_taskstatuses(self, target, flag, data, method):
        if not flag:
            if method == 'GET':
                params = self.get_url_parameters(target)
                if params:
                    statuses = self.generator_get_filtered_resource('taskstatuses', params)
                else:
                    statuses = self.generator_get_all_resource('taskstatuses')
                return RESPONSE_HEADERS, statuses[0]
            else:
                self.raise_error('400')
        else:
            self.raise_error('401')

    def call_applications(self, target, flag, data, method):
        if not flag:
            if method == 'GET':
                params = self.get_url_parameters(target)
                if params:
                    applications = self.generator_get_filtered_resource('application', params)
                else:
                    applications = self.generator_get_all_resource('application')

                return RESPONSE_HEADERS, {'applications': applications}
            elif method == 'POST':
                if data:
                    self.generator_add_resource('application', resource_data=data)

                    return RESPONSE_HEADERS, ''
            self.raise_error('405')
        else:
            self.raise_error('401')

    def get_projects(self, target, flag, data, method):
        if not flag:
            projects = self.generator_get_filtered_resource('project', self.get_url_parameters(target))

            return RESPONSE_HEADERS, {'projects': projects}
        else:
            self.raise_error('401')

    def get_tasks(self, target, flag, data, method):
        if not flag:
            params = self.get_url_parameters(target)
            if params.get('project'):
                return RESPONSE_HEADERS, {'tasks': self.generator_get_filtered_resource('task', params)}
            self.raise_error('500', {"error": "A GET request on the Tasks resource must be filtered by project."})
        else:
            self.raise_error('401')

    def call_task(self, target, flag, data, method):
        if not flag:
            task_id = target.split('/')[-1].split('-')[1]
            task_number = re.sub('[^\d]+', '', task_id)

            if not self.generator_resource_exists('task', task_number):
                self.raise_error('404', {'error': 'Not Found'})
            if method == 'GET':
                # We will return the task at the end
                pass
            elif method == 'PUT' or method == 'POST':
                if data:
                    self.generator_update_resource('task', task_number, data)
                else:
                    self.raise_error('400', {'error': 'Missing data param'})
            else:
                self.raise_error('400', {'error': 'Bad Request'})

            return RESPONSE_HEADERS, self.generator_get_resource('task', task_number)
        else:
            self.raise_error('401')

    def call_task_notes(self, target, flag, data, method):
        if not flag:
            _target = target.split('/')
            if len(_target) == 4:
                note_type = _target[3]
            else:
                note_type = ''

            if method == 'GET':
                return RESPONSE_HEADERS, self._get_tasknotes(flag, self.get_url_parameters(target), note_type)
            elif method == 'POST':
                return RESPONSE_HEADERS, self._post_tasknote(flag, data, note_type)
        self.raise_error('401')

    def _get_tasknotes(self, flag, data, note_type):
        if note_type not in ['', 'ide', 'text', 'analysis']:
            self.raise_error('500')
        elif note_type == '':
            note_types = ['text', 'ide', 'analysis']
        else:
            note_types = ['%s' % note_type]

        response = {}

        for note_type in note_types:
            if self.is_data_valid(data, ['task']):
                response[note_type] = self.generator_get_filtered_resource('%s_note' % note_type, data)
            else:
                response[note_type] = self.generator_get_all_resource('%s_note' % note_type)

        return response

    def _post_tasknote(self, flag, data, note_type):
        if note_type not in ['ide', 'text', 'analysis']:
            self.raise_error('500')
        task_number = self.extract_task_number_from_title(data['task'])
        note_type = '%s_note' % note_type

        if not self.generator_resource_exists('task', task_number):
            self.raise_error('404', 'Task not found %s' % task_number)

        if note_type == 'text_note' and self.is_data_valid(data, ['text', 'task']):
            data['display_text'] = '<p>%s</p>' % data['text']
        elif note_type == 'ide_note' and self.is_data_valid(data, ['text', 'task', 'filename', 'status']):
            data['display_text'] = '<p>%s</p>' % data['text']
        elif note_type == 'analysis_note' and self.is_data_valid(data, ['task', 'project_analysis_note', 'confidence', 'findings']):
            if not data['findings']:
                data['status'] = 'partial'
            else:
                data['status'] = 'failed'
                data['confidence'] = 'high'
        else:
            self.raise_error('500', {'error': 'Missing parameter'})

        self.generator_add_resource(note_type, resource_data=data)

        return self.generate_resource_from_template(note_type, data)

    def add_project_analysis_note(self, target, flag, data, method):
        if not flag:
            if method == 'POST':
                if not self.is_data_valid(data, ['analysis_ref']) or not data['analysis_ref']:
                    self.raise_error(400)

                if self.is_data_valid(data, ['analysis_type']) and data['analysis_type'] in self.analysis_tools:
                    self.generator_add_resource('project_analysis_note', resource_data=data)

                    return RESPONSE_HEADERS, self.generate_resource_from_template('project_analysis_note', data)
            self.raise_error('500')
        else:
            self.raise_error('401')