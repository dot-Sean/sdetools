import os
import re
import random

from sdetools.sdelib.testlib.alm_response_generator import ResponseGenerator


class SdeResponseGenerator(ResponseGenerator):
    STATUS_NAMES = ['open', 'closed']
    BASE_PATH = 'api'
    ANALYSIS_TOOLS = ['appscan', 'veracode', 'fortify', 'webinspect']

    def __init__(self, host, app_name, project_name, protocol='http'):
        initial_task_status = self.STATUS_NAMES[0]
        test_dir = os.path.dirname(os.path.abspath(__file__)) 
        super(SdeResponseGenerator, self).__init__(initial_task_status, test_dir)

        self.app_name = app_name
        self.project_name = project_name
        self.api_url = '%s://%s/%s' % (protocol, host, self.BASE_PATH)
        self.rest_api_targets = {
            'applications': 'call_applications',
            'projects': 'get_projects',
            'tasks$': 'get_tasks',
            'tasks/[0-9]+-[0-9a-zA-z]+': 'call_task',
            'tasknotes.*': 'call_task_notes',
            'projectnotes/analysis$': 'add_project_analysis_note'
        }

    def add_default_tasks(self):
        self.generator_add_task('40', 'T40: Task Name')
        self.generator_add_task('36', 'T36: Task Name')
        self.generator_add_task('38', 'T38: Task Name')

    def generator_add_task(self, task_number, task_name=None, status=None):
        if not self.generator_get_task(task_number):
            if not task_name:
                task_name = "T%s" % task_number
            if not status:
                status = self.initial_task_status

            self.alm_tasks[task_number] = {
                "name": task_name,
                "id": task_number,
                "status": status,
                "timestamp": self.get_current_timestamp(),
                "text_notes": [],
                "ide_notes": [],
                "analysis_notes": [],
                "task_id": '1000-T%s' % task_number
            }

    def generate_sde_task(self, task_number=None, project_id=1000, status='TODO', priority=7):
        if task_number is None:
            task_number = random.randint(50, 999999999)

        self.generator_add_task(task_number, status=status)

        return self._generate_task(task_number, project_id, status, priority)

    """
       Response functions 
    """
    def call_applications(self, target, flag, data, method):
        if not flag:
            if method == 'GET':
                response = {'applications': []}

                if self.is_data_valid(data, ['name']):
                    app_name = data['name']
                    if app_name != self.app_name:
                        return response

                application = self.get_json_from_file('application')
                application['name'] = self.app_name
                response['applications'].append(application)

                return response
            elif method == 'POST':
                # Create application
                if data:
                    return None

            self.raise_error('405')
        else:
            self.raise_error('401')

    def get_projects(self, target, flag, data, method):
        if not flag:
            response = {'projects': []}

            if self.is_data_valid(data, ['name']):
                project_name = data['name']
                project = self.get_json_from_file('project')
                project['name'] = project_name
                response['projects'].append(project)

            return response
        else:
            self.raise_error('401')

    def get_tasks(self, target, flag, data, method):
        if not flag:
            if data and data['project']:
                project_id = data['project']
                tasks = []

                for task_number in self.generator_get_all_tasks():
                    task = self.generator_get_task(task_number)
                    _task = self._generate_task(task_number, project_id, task['status'])
                    _task['text_notes'] = task['text_notes']
                    _task['ide_notes'] = task['ide_notes']
                    _task['analysis_notes'] = task['analysis_notes']
                    tasks.append(_task)

                return {'tasks': tasks}
            else:
                self.raise_error('500', {
                    "error": "A GET request on the Tasks resource must be filtered by project."
                })
        else:
            self.raise_error('401')

    def call_task(self, target, flag, data, method):
        if not flag:
            task_combo_id = re.search('(?<=tasks/).*', target).group(0)
            project_id, task_id = task_combo_id.split('-')
            task_number = re.sub('T', '', task_id)
            task = self.generator_get_task(task_number)

            if method == 'GET':
                if task:
                    return self._generate_task(task_number, project_id)
                else:
                    self.raise_error('500', {'error': 'Not Found'})
            elif method == 'PUT':
                if self.is_data_valid(data) and task:
                    status = data['status']
                    self.generator_update_task(task_number, 'status', status)

                    return self._generate_task(task_number, project_id)
                else:
                    self.raise_error('500', {'error': 'Not Found'})
        else:
            self.raise_error('401')

    def call_task_notes(self, target, flag, data, method):
        if not flag:
            if target == 'tasknotes':
                note_type = ''
            else:
                note_type = target.split('/')[1]

            if note_type not in ['', 'ide', 'text', 'analysis']:
                self.raise_error('500')
            if method == 'GET':
                return self._get_tasknotes(flag, data, note_type)
            elif method == 'POST':
                return self._post_tasknote(flag, data, note_type)
        self.raise_error('401')

    def _get_tasknotes(self, flag, data, note_type):
        response = {}
        text_notes = []
        ide_notes = []
        analysis_notes = []
        if self.is_data_valid(data, ['task']):
            tasks = [self.extract_task_number_from_title(data['task'])]
        else:
            tasks = self.generator_get_all_tasks

        for task_number in tasks:
            _task = self.generator_get_task(task_number)

            if not _task:
                self.raise_error('500', {'error': 'Not Found'})
            if note_type in ['', 'text']:
                notes = _task['text_notes']

                for note in notes:
                    text_note = self._generate_task_note_with_values('text', note)
                    response['text'].append(text_note)
            if note_type in ['', 'ide']:
                notes = _task['ide_notes']

                for note in notes:
                    ide_note = self._generate_task_note_with_values('ide', note)
                    ide_notes.append(ide_note)
            if note_type in ['', 'analysis']:
                notes = _task['analysis_notes']

                for note in notes:
                    analysis_note = self._generate_task_note_with_values('analysis', note)
                    analysis_notes.append(analysis_note)

        if note_type in ['', 'text']:
            response['text'] = text_notes
        if note_type in ['', 'ide']:
            response['ide'] = ide_notes
        if note_type in ['', 'analysis']:
            response['analysis'] = analysis_notes

        return response

    def _post_tasknote(self, flag, data, note_type):
        task = data['task']
        task_number = self.extract_task_number_from_title(task)
        _task = self.generator_get_task(task_number)

        if note_type == 'text' and self.is_data_valid(data, ['text', 'task']):
            new_text_notes = _task['text_notes']
            new_text_notes.append(data)
            self.generator_update_task(task_number, 'text_notes', new_text_notes)

            return self._generate_task_note_with_values('text', data)
        elif note_type == 'ide' and self.is_data_valid(data, ['text', 'task', 'filename', 'status']):
            new_ide_notes = _task['ide_notes']
            new_ide_notes.append(data)
            self.generator_update_task(task_number, 'ide_notes', new_ide_notes)

            return self._generate_task_note_with_values('ide', data)
        elif note_type == 'analysis' and self.is_data_valid(data, ['task', 'project_analysis_note', 'confidence', 'findings']):
            new_analysis_notes = _task['analysis_notes']

            if not data['findings']:
                data['status'] = 'partial'
            else:
                data['status'] = 'failed'
                data['confidence'] = 'high'

            new_analysis_notes.append(data)
            self.generator_update_task(task_number, 'analysis_notes', new_analysis_notes)

            return self._generate_task_note_with_values('analysis', data)
        else:
            self.raise_error('500', {'error': 'Missing parameter'})

    def add_project_analysis_note(self, target, flag, data, method):
        if not flag:
            if not data:
                self.raise_error('500')
            else:
                if data['analysis_type'] in self.ANALYSIS_TOOLS:
                    response = self.get_json_from_file('project_analysis_note')
                    response['analysis_ref'] = data['analysis_ref']
                    response['project'] = data['project']
                    response['analysis-type'] = data['analysis_type']

                    return response
                else:
                    self.raise_error('500')
        else:
            self.raise_error('401')

    """
        JSON Generator
    """
    def _generate_task(self, task_number, project_id=1000, status='TODO', priority=7):
        if task_number in ['36', '38', '40']:
            task = self.get_json_from_file('T%s' % task_number)
        else:
            task = self.get_json_from_file('task')
            task['title'] = 'T%s' % task_number
            task['priority'] = priority

        task['status'] = status
        task['id'] = '%s-T%s' % (project_id, task_number)
        task['project'] = project_id

        return task

    def _generate_task_note_with_values(self, note_type, fields):
        task_note = self.get_json_from_file('%s_note' % note_type)

        for field in fields:
            if field in task_note:
                value = fields.get(field)

                if field == 'text':
                    task_note['text'] = value
                    task_note['display_text'] = "<p>%s</p>" % value
                else:
                   task_note[field] = value
            else:
                self.raise_error('500', {'error': 'Field %s does not exist in task note' % field})

        return task_note