from sdetools.sdelib.restclient import RESTBase, APIError
from sdetools.alm_integration.alm_plugin_base import AlmException
from sdetools.modules.sync_jira.jira_shared import JIRATask

class JIRARestAPI(RESTBase):
    """ Base plugin for JIRA """
    # the fields we are ready to set, at a minimum
    BASE_FIELDS = ['project', 'summary', 'labels', 'priority', 'versions', 'parent',
                   'description', 'issuetype', 'reporter']

    def __init__(self, config):
        super(JIRARestAPI, self).__init__('alm', 'JIRA', config, 'rest/api/2')
        self.versions = None
        self.custom_fields = []
        self.fields = []

    def parse_response(self, result, headers):
        if result == "":
            return "{}"
        else:
            return super(JIRARestAPI, self).parse_response(result, headers)

    def connect_server(self):
        """ Verifies that JIRA connection works """
        # Verify that we can connect to JIRA
        try:
            self.call_api('project')
        except APIError, err:
            raise AlmException('Unable to connect to JIRA service (Check server URL, '
                    'user, pass). Reason: %s' % str(err))

    def connect_project(self):
        # Verify that we can access project by retrieving its versions
        try:
            self.versions = self.call_api('project/%s/versions' % (self.urlencode_str(self.config['alm_project'])))
        except APIError:
            raise AlmException('JIRA project not found: %s' % self.config['alm_project'])

    def _has_priority(self, priority_name):
        """
        Check that the priority exists
        """
        if not self.fields:
            return False
        elif 'priority' not in self.fields:
            return True

        for priority_option in self.fields['priority']['allowedValues']:
            if priority_option['name'] == priority_name:
                return True

        return False

    def setup_fields(self, issue_type_id):

        try:
            meta_info = self.call_api('issue/createmeta', method=self.URLRequest.GET,
                                      args={'projectKeys': self.config['alm_project'],
                                      'expand': 'projects.issuetypes.fields'})
        except APIError:
            raise AlmException('Could not retrieve fields for JIRA project: %s' % self.config['alm_project'])

        for item in meta_info['projects'][0]['issuetypes']:
            if item['name'] == self.config['jira_issue_type']:
                for key in item['fields'].keys():
                    self.fields.append({
                        'id': key,
                        'name': item['fields'][key]['name'],
                        'required': item['fields'][key]['required'],
                        'schema': item['fields'][key]['schema'],
                    })
                break

        assigned_fields = JIRARestAPI.BASE_FIELDS[:]

        missing_fields = []
        required_fields = {}

        for field in self.fields:
            if field['required']:
                required_fields[field['id']] = field

        if self.config['alm_custom_fields']:
            for key in self.config['alm_custom_fields']:
                for field in self.fields:
                    if key == field['name']:
                        self.custom_fields.append({
                            'field': field['id'],
                            'value': self.config['alm_custom_fields'][key],
                            'schema': field['schema']
                        })
                        assigned_fields.append(field['id'])

        for field in required_fields.keys():
            if field not in assigned_fields:
                missing_fields.append(required_fields[field]['name'])

        if len(missing_fields) > 0:
            raise AlmException('The following fields are missing values: %s' % ', '.join(missing_fields))
        
    def has_field(self, field_name):
        if not self.fields:
            return False
             
        for field in self.fields:
            if field_name == field['id']:
                return True
                
        return False
        
    def get_issue_types(self):
        try:
            return self.call_api('issuetype')
        except APIError:
            raise AlmException('Unable to get issuetype from JIRA API')

    def get_subtask_issue_types(self):
        return self.get_issue_types()

    def get_task(self, task, task_id):
        try:
            url = 'search?jql=project%%3D\'%s\'%%20AND%%20summary~\'%s%%5C%%5C:\'' % (
                    self.config['alm_project'], task_id)
            result = self.call_api(url)
        except APIError:
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
        if 'versions' in jtask['fields'] and jtask['fields']['versions']:
            for version in jtask['fields']['versions']:
                task_versions.append(version['name'])

        task_priority = None
        if 'priority' in jtask['fields'] and jtask['fields']['priority']:
            task_priority = jtask['fields']['priority']['name']

        return JIRATask(task_id,
                        jtask['key'],
                        task_priority,
                        jtask['fields']['status']['name'],
                        task_resolution,
                        jtask['fields']['updated'],
                        self.config['jira_done_statuses'],
                        task_versions)

    def set_version(self, task, project_version):
        # REST allows us to add versions ad hoc
        try:
            remote_url = 'issue/%s' % task.get_alm_id()
            version_update = {'update': {'versions': [{'add': {'name': project_version}}]}}
            self.call_api(remote_url, method=self.URLRequest.PUT, args=version_update)
        except APIError:
            raise AlmException('Unable to update issue %s with new version %s' % (task.get_alm_id(), project_version))

    def add_task(self, task, issue_type_id, project_version):
        affected_versions = []
        if self.config['alm_project_version']:
            affected_versions.append({'name': self.config['alm_project_version']})

        #Add task
        args = {
           'fields': {
               'project': {
                   'key': self.config['alm_project']
               },
               'summary': task['title'],
               'issuetype': {
                   'id': issue_type_id
               },
           }
        }
        if self.has_field('description'):
            args['fields']['description'] = task['formatted_content']

        if self.has_field('reporter'):
            args['fields']['reporter'] = {'name': self.config['alm_user']}

        if self.has_field('labels'):
            args['fields']['labels'] = ['SD-Elements']

        if self.has_field('priority'):
            args['fields']['priority'] = {'name': task['alm_priority']}

        if affected_versions:
            args['fields']['versions'] = affected_versions

        if self.config['alm_parent_issue']:
            args['fields']['parent'] = {'key': self.config['alm_parent_issue']}

        for field in self.custom_fields:
            if 'custom' not in field['schema']:
                continue

            if field['schema']['custom'] == 'com.atlassian.jira.plugin.system.customfieldtypes:textfield':
                args['fields'][field['field']] = field['value']
            elif field['schema']['custom'] == 'com.atlassian.jira.plugin.system.customfieldtypes:textarea':
                args['fields'][field['field']] = field['value']
            elif field['schema']['custom'] == 'com.atlassian.jira.plugin.system.customfieldtypes:select':
                args['fields'][field['field']] = {'value': field['value']}
            elif field['schema']['custom'] == 'com.atlassian.jira.plugin.system.customfieldtypes:radiobuttons':
                args['fields'][field['field']] = {'value': field['value']}
            elif field['schema']['custom'] == 'com.atlassian.jira.plugin.system.customfieldtypes:multiselect':
                args['fields'][field['field']] = [{'value': field['value']}]
            elif field['schema']['custom'] == 'com.atlassian.jira.plugin.system.customfieldtypes:multicheckboxes':
                args['fields'][field['field']] = [{'value': field['value']}]

        # Create the issue in JIRA
        try:
            issue = self.call_api('issue', method=self.URLRequest.POST, args=args)
        except APIError, err:
            raise AlmException('Unable to add issue to JIRA. Reason: %s' % err)

        try:
            # Add a link back to SD Elements
            remote_url = 'issue/%s/remotelink' % issue['key']
            args = {"object": {"url": task['url'], "title": task['title']}}
            self.call_api(remote_url, method=self.URLRequest.POST, args=args)
            
        except APIError:
            # This is not a terrible thing, the user may not have permission
            # and I don't think we should enforce that they do
            pass

        return issue

    def get_available_transitions(self, task_id):
        trans_url = 'issue/%s/transitions' % task_id
        ret_trans = {}
        try:
            transitions = self.call_api(trans_url)
        except APIError:
            raise AlmException("Unable to get transition IDS for JIRA task %s" % task_id)
        for transition in transitions['transitions']:
            ret_trans[transition['name']] = transition['id']
        return ret_trans

    def remove_task(self, task):
        delete_url = 'issue/%s' % task.get_alm_id()
        try:
            self.call_api(delete_url, method=self.URLRequest.DELETE)
        except self.APIFormatError:
            # The response does not have JSON, so it is incorrectly raised as
            # a JSON formatting error. Ignore this error
            pass
        except APIError, err:
            raise AlmException("Unable to delete task : %s" % err)

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
