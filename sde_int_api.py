from sdetools.sdelib import restclient 


class InternalAPI(restclient):
    """
    Note: In all the API calls:
    - a 'project' arg variable is the project id
    - a 'task' arg variable is in the format <project_id>-<task_id>
        e.g. '127-T106'
    """

    def __init__(self, conf_prefix, conf_name, config):
        pass

    def get_applications(self, **filters):
        """
        Gets all applications accessible to user

        Available Filters:
            name -> application name to be searched for
        """
        result = self.call_api('applications', args=filters)
        return result['applications']

    def get_projects(self, application, **filters):
        """
        Gets all projects for parameter application

        Available Filters:
            name -> project name to be searched for
        """
        args = {'application': application}
        args.update(filters)
        result = self.call_api('projects', args=args)
        return result['projects']

    def get_tasks(self, project):
        """ 
        Get all tasks for a project indicated by the ID of the project
        """
        result = self.call_api('tasks', args={'project': project})
        return result['tasks']

    def get_task(self, task):
        """ 
        Get an individual task with parameter task id
        <task> = <project_id>-<task_id> (e.g. 127-T21)
        """
        result = self.call_api('tasks/%s' % task)
        return result

    def add_task_text_note(self, task, text):
        note = {'text':text, 'task':task}
        result = self.call_api('tasknotes/text', self.URLRequest.POST, args=note)
        return result

    def add_task_ide_note(self, task, text, filename, status):
        note = {'text': text, 'filename': filename, 'status': status, 'task': task}
        result = self.call_api('tasknotes/ide', self.URLRequest.POST, args=note)
        return result

    def get_task_notes(self, task, note_type):
        end_point = 'tasknotes'
        if note_type not in ['', 'ide', 'text']:
            return
        if note_type:
            end_point += '/%s' % (note_type)
        return self.call_api(end_point, args={'task': task})

    def add_analysis_note(self, task, analysis_ref, confidence, findings):
        note = {'task': task, 'project_analysis_note': analysis_ref, 'confidence': confidence, 'findings': findings}
        return self.call_api('tasknotes/analysis', self.URLRequest.POST, args=note)

    def add_project_analysis_note(self, project_id, analysis_ref, analysis_type):
        project_analysis = {'project': project_id, 'analysis_ref': analysis_ref, 'analysis_type': analysis_type}
        return self.call_api('projectnotes/analysis', self.URLRequest.POST, args=project_analysis)

    def update_task_status(self, task, status):
        """
        Update the task status. The task ID should include the project number
        Returns the 'status' field of he result
        """
        result = self.call_api('tasks/%s' % task, self.URLRequest.PUT, args={'status': status})
        return result['status']
