from sdetools.sdelib.restclient import RESTBase, APIError
from sdetools.alm_integration.alm_plugin_base import AlmException
from sdetools.modules.sync_jira.jira_shared import JIRATask

class JIRARestAPI(RESTBase):
    """ Base plugin for JIRA """

    def __init__(self, config):
        super(JIRARestAPI, self).__init__('alm', 'JIRA', config, 'rest/api/2')
        self.versions = None

    def parse_response(self, result):
        if result == "":
            return "{}"
        else:
            return super(JIRARestAPI, self).parse_response(result)

    def connect(self):
        """ Verifies that JIRA connection works """
        #verify that we can connect to JIRA
        try:
            result = self.call_api('project')
        except APIError:
            raise AlmException('Unable to connect to JIRA. Check server URL, ID, password')

        #verify that we can access project by retrieving its versions
        try:
            self.versions = self.call_api('project/%s/versions' % (self.urlencode_str(self.config['alm_project'])))
        except APIError:
            raise AlmException('Unable to connect to JIRA project %s' % self.config['alm_project'])

    def get_issue_types(self):
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

        task_resolution = None
        if 'resolution' in jtask['fields'] and jtask['fields']['resolution']:
            task_resolution = jtask['fields']['resolution']['name']

        task_versions = []
        if jtask['fields']['versions']:
            for version in jtask['fields']['versions']:
                task_versions.append(version['name'])

        return JIRATask(task['id'],
                        jtask['key'],
                        jtask['fields']['priority']['name'],
                        jtask['fields']['status']['name'],
                        task_resolution,
                        jtask['fields']['updated'],
                        self.config['jira_done_statuses'],
                        task_versions)

    def set_version(self, task, project_version):
        # REST allows us to add versions ad hoc
        try:
            remoteurl_url = 'issue/%s' % task.get_alm_id()
            version_update = {'update':{'versions':[{'add':{'name':project_version}}]}}
            self.call_api(remoteurl_url, method=self.URLRequest.PUT, args=version_update)
        except APIError:
            raise AlmException('Unable to update issue %s with new version %s' % (task.get_alm_id(), project_version))

    def add_task(self, task, issue_type_id, project_version):
        affected_versions = []
        if self.config['alm_project_version']:
            affected_versions.append({'name':self.config['alm_project_version']})

        #Add task
        args = {
           'fields': {
               'project': {
                   'key': self.config['alm_project']
               },
               'summary': task['title'],
               'description': task['formatted_content'],
               'priority': {
                   'name': task['alm_priority']
               },
               'issuetype': {
                   'id': issue_type_id
               },
               'versions': affected_versions,
               'labels':['SD-Elements']
           }
        }
        try:
            issue = self.call_api('issue', method=self.URLRequest.POST, args=args)
            
            # Add a link back to SD Elements
            remoteurl_url = 'issue/%s/remotelink' % issue['key']
            args = {"object": {"url":task['url'],"title":task['title']}}
            self.call_api(remoteurl_url, method=self.URLRequest.POST, args=args)
            
            return issue
        except APIError:
            raise AlmException('Unable to add issue to JIRA')

    def get_available_transitions(self, task_id):
        trans_url = 'issue/%s/transitions' % task_id
        ret_trans = {}
        try:
            transitions = self.call_api(trans_url)
        except APIError, err:
            raise AlmException("Unable to get transition IDS for JIRA task %s" % task_id)
        for transition in transitions['transitions']:
            ret_trans[transition['name']] = transition['id']
        return ret_trans

    def update_task_status(self, task_id, status_id):
        trans_url = 'issue/%s/transitions' % task_id
        trans_args = {'transition': {'id': status_id}}
        try:
            self.call_api(trans_url, args=trans_args, method=self.URLRequest.POST)
        except self.APIFormatError:
            # The response does not have JSON, so it is incorrectly raised as
            # a JSON formatting error. Ignore this error
            pass
        except APIError, err:
            raise AlmException("Unable to set task status: %s" % err)
