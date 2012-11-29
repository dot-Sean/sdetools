from restclient import RESTBase
from restclient import APIError, APIHTTPError, APICallError, APIAuthError, ServerError, APIFormatError

import logging
logger = logging.getLogger(__name__)

class APIBase(RESTBase):
    def __init__(self, config):
        super(APIBase, self).__init__('sde', 'SD Elements', config, 'api')
        self.app = None
        self.prj = None

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
        args = {'application':application}
        args.update(filters)
        result = self.call_api('projects', args=args)
        return result['projects']

    def get_tasks(self, project):
        result = self.call_api('tasks', args={'project':project})
        return result['tasks']

    def get_task(self, task):
        """ Gets an individual task with parameter task id"""
        result = self.call_api('tasks/%s' % task)
        return result

    def add_task_text_note(self, task, text):
        note = {'text':text, 'task':task}
        result = self.call_api('tasknotes/text', self.URLRequest.POST, args=note)
        return result

    def add_task_ide_note(self, task, text, filename, status):
        note = {'text':text, 'filename':filename, 'status':status, 'task':task}
        result = self.call_api('tasknotes/ide', self.URLRequest.POST, args=note)
        return result

    def get_task_notes(self, task):
        return self.call_api('tasknotes', args={'task':task})

    def get_task_text_notes(self, task):
        return self.call_api('tasknotes/text', args={'task':task})

    def get_task_ide_notes(self, task):
        return self.call_api('tasknotes/ide', args={'task':task})

    def update_task_status(self, task, status):
        """
        Update the task status. The task ID should include the project number
        """
        #TODO: regular expression on task and status for validation
        result = self.call_api('tasks/%s' % task, self.URLRequest.PUT,
            args={'status':status})
        return result['status']
