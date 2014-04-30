from commons import UsageError, json
import restclient

import logging
logger = logging.getLogger(__name__)


def _encode_options(options):
    headers = {'Accept': 'application/json;'}
    for item in options:
        headers['Accept'] += '; %s=%s' % (item, json.dumps(json.dumps(options[item])))
    return headers

class ExtAPI(restclient.RESTBase):
    """
    Note: In all the API calls:
    - a 'project' arg variable is the project id
    - a 'task' arg variable is in the format <project_id>-<task_id>
        e.g. '127-T106'
    """

    def __init__(self, config):
        extra_conf_opts = [('sde_api_token', 'SDE API Token', '')]
        super(ExtAPI, self).__init__('sde', 'SD Elements', config, 'api', extra_conf_opts)
        self.connected = False

    def post_conf_init(self):
        if self._get_conf('api_token'):
            if '@' not in self._get_conf('api_token'):
                raise UsageError('Unable to process API Token')
            self.config['sde_user'] = None
            self.config['sde_pass'], self.config['sde_server'] = (
                self.config['sde_api_token'].split('@', 1))
            self.set_auth_mode('api_token')

        super(ExtAPI, self).post_conf_init()

    def connect(self):
        if self.config['authmode'] == 'session':
            self.set_auth_mode('session')
            result = True
        else:
            #TODO: Find a better alternative ->
            #In 'basic' mode, we make an extra call just to verify that credentials are correct
            result = self.get_applications()
        self.connected = True
        return not not result

    def get_applications(self, options={}, **filters):
        """
        Gets all applications accessible to user

        Available Filters:
            name -> application name to be searched for
        """
        result = self.call_api('applications', args=filters,
                call_headers=_encode_options(options))
        return result['applications']

    def create_application(self, name):
        args = {'name': name}
        return self.call_api('applications', self.URLRequest.POST, args=args)

    def get_projects(self, application, options={}, **filters):
        """
        Gets all projects for parameter application

        Available Filters:
            name -> project name to be searched for
        """
        args = {'application': application}
        args.update(filters)
        result = self.call_api('projects', args=args,
                call_headers=_encode_options(options))
        return result['projects']

    def get_tasks(self, project, options={}, **filters):
        """
        Get all tasks for a project indicated by the ID of the project
        """
        args = {'project': project}
        args.update(filters)
        result = self.call_api('tasks', args=args, call_headers=_encode_options(options))
        return result['tasks']

    def get_task(self, task, options={}, **filters):
        """
        Get an individual task with parameter task id
        <task> = <project_id>-<task_id> (e.g. 127-T21)
        """
        end_point = 'tasks/%s' % task
        return self.call_api(end_point, args=filters, call_headers=_encode_options(options))

    def add_task_text_note(self, task, text):
        note = {
            'text': text,
            'task': task}
        return self.call_api('tasknotes/text', self.URLRequest.POST, args=note)

    def add_task_ide_note(self, task, text, filename, status):
        note = {
            'text': text,
            'filename': filename,
            'status': status,
            'task': task}
        return self.call_api('tasknotes/ide', self.URLRequest.POST, args=note)

    def get_task_notes(self, task, note_type, options={}, **filters):
        end_point = 'tasknotes'
        if note_type not in ['', 'ide', 'text', 'analysis']:
            return
        if note_type:
            end_point += '/%s' % (note_type)
        args = {'task': task}
        args.update(filters)
        return self.call_api(end_point, args=args, call_headers=_encode_options(options))

    def add_analysis_note(self, task, analysis_ref, confidence, findings, behaviour):
        note = {
            'task': task,
            'project_analysis_note': analysis_ref,
            'confidence': confidence,
            'findings': findings,
            'behaviour': behaviour}
        return self.call_api('tasknotes/analysis', self.URLRequest.POST, args=note)

    def add_project_analysis_note(self, project_id, analysis_ref, analysis_type):
        project_analysis = {
            'project': project_id,
            'analysis_ref': analysis_ref,
            'analysis_type': analysis_type}
        return self.call_api('projectnotes/analysis', self.URLRequest.POST, args=project_analysis)

    def update_task_status(self, task, status):
        """
        Update the task status. The task ID should include the project number
        Returns the 'status' field of he result
        """
        #TODO: regular expression on task and status for validation
        result = self.call_api('tasks/%s' % task, self.URLRequest.PUT,
            args={'status': status})
        return result['status']

    def get_phases(self, options={}, **filters):
        """
        Get all phases for an organization
        """
        return self.call_api('phases', args=filters, call_headers=_encode_options(options))


APIBase = ExtAPI

