from sdelib.restclient import RESTBase, APIError
from alm_integration.alm_plugin_base import AlmException
from modules.sync_jira.jira_shared import JIRATask

class JIRARestAPI(RESTBase):
    """ Base plugin for JIRA """

    def __init__(self, config):
        super(JIRARestAPI, self).__init__('alm', 'JIRA', config, 'rest/api/2')

    def connect(self):
        """ Verifies that JIRA connection works """
        #verify that we can connect to JIRA
        try:
            result = self.call_api('project')
        except APIError:
            raise AlmException('Unable to connect to JIRA. Check server URL, ID, password')

        #verify that we can access project
        try:
            self.call_api('project/%s' % (self.config['alm_project']))
        except APIError:
            raise AlmException('Unable to connect to JIRA project %s' % self.config['alm_project'])

    def get_issue_type(self):
        try:
            return self.call_api('issuetype')
        except APIError:
            raise AlmException('Unable to get issuetype from JIRA API')

    def get_task(self, task, task_id):
        try:
            url = 'search?jql=project%%3D\'%s\'%%20AND%%20summary~\'%s\'' % (
                    self.config['alm_project'], task_id)
            result = self.call_api(url)
        except APIError, err:
            raise AlmException("Unable to get task %s from JIRA" % task_id)

        if not result['total']:
            #No result was found from query
            return None
        #We will use the first result from the query
        jtask = result['issues'][0]

        #We will use the first result from the query
        jtask = result['issues'][0]
        resolution = None
        if jtask['fields']['resolution']:
            resolution = jtask['fields']['resolution']['name']
        return JIRATask(task['id'],
                        jtask['key'],
                        jtask['fields']['priority']['name'],
                        jtask['fields']['status']['name'],
                        resolution,
                        jtask['fields']['updated'],
                        self.config['jira_done_statuses'])

    def add_task(self, task):
        #Add task
        args = {
           'fields': {
               'project': {
                   'key': self.config['alm_project']
               },
               'summary': task['title'],
               'description': task['content'],
               'priority': {
                   'name': JIRATask.translate_priority(task['priority'])
               },
               'issuetype': {
                   'id': self.jira_issue_type_id
               }
           }
        }
        try:
            return self.call_api('issue', method=self.URLRequest.POST, args=args)
        except APIError:
            logger.exception('Unable to add issue to JIRA')
            return None
