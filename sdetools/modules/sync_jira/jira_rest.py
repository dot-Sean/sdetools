from sdetools.sdelib.restclient import RESTBase, APIError
from sdetools.alm_integration.alm_plugin_base import AlmException
from sdetools.modules.sync_jira.jira_shared import JIRATask
from sdetools.sdelib.commons import json


class JIRARestAPI(RESTBase):
    """ Base plugin for JIRA """
    # the fields we are ready to set, at a minimum
    BASE_FIELDS = ['project', 'summary', 'labels', 'priority', 'versions', 'parent',
                   'description', 'issuetype', 'reporter']

    def __init__(self, config):
        super(JIRARestAPI, self).__init__('alm', 'JIRA', config, 'rest/api/2')
        self.versions = None
        self.custom_fields = {}
        self.custom_lookup_fields = []
        self.fields = {}

    def parse_response(self, result, headers):
        if result == "":
            return "{}"
        else:
            return super(JIRARestAPI, self).parse_response(result, headers)

    def parse_error(self, result):
        # Try to parse the response as JSON
        try:
            error_response = json.loads(result)
        except ValueError:
            return result

        # Send back all the error messages in one go
        if 'errorMessages' in error_response and error_response['errorMessages']:
            return ' '.join(error_response['errorMessages'])
        elif 'errors' in error_response:
            error_messages = []
            for field, field_message in error_response['errors'].items():
                error_messages.append('%s: %s' % (field, field_message))
            return ' '.join(error_messages)
        else:
            return result

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

    def _get_field_meta(self, all_field_meta, field_name):
        # Jira maps a field to one or many internal JQL filter names - pick one
        for field in all_field_meta:
            if field['name'] == field_name:
                return field
        return None

    def setup_fields(self, issue_type_id):
        # Retrieve field meta information for the chosen issue type
        try:
            meta_info = self.call_api('issue/createmeta', method=self.URLRequest.GET,
                                      args={'projectKeys': self.config['alm_project'],
                                      'expand': 'projects.issuetypes.fields'})
        except APIError, error:
            raise AlmException('Could not retrieve fields for JIRA project: %s. %s' %
                               (self.config['alm_project'], error))

        for item in meta_info['projects'][0]['issuetypes']:
            if item['name'] == self.config['jira_issue_type']:
                self.fields = item['fields']
                break

        if not self.fields:
            raise AlmException('Issue type %s not available for project %s' %
                               (self.config['jira_issue_type'], self.config['alm_project']))

        assigned_fields = JIRARestAPI.BASE_FIELDS[:]

        missing_fields = []

        if self.config['alm_custom_fields']:
            for key, value in self.config['alm_custom_fields'].iteritems():
                for field_id, field_details in self.fields.iteritems():
                    if key == field_details['name']:
                        self.custom_fields[field_id] = value
                        assigned_fields.append(field_id)

        # Get all fields from the system to help with custom lookups
        if self.config['alm_custom_lookup_fields']:
            try:
                all_fields_meta = self.call_api('field', method=self.URLRequest.GET)
            except APIError, error:
                raise AlmException('Could not retrieve sql search for JIRA project: %s. %s' %
                                   (self.config['alm_project'], error))

            for key, value in self.config['alm_custom_lookup_fields'].iteritems():
                for field_id, field_details in self.fields.iteritems():
                    if key == field_details['name']:
                        field_meta = self._get_field_meta(all_fields_meta, key)
                        if field_meta:
                            self.custom_lookup_fields.append({
                                'meta': field_meta,
                                'value': value
                            })
                        else:
                            raise AlmException('No filter name found for: %s' % key)

        for field_id, field_details in self.fields.iteritems():
            if field_details['required'] and field_id not in assigned_fields:
                missing_fields.append(field_details['name'])

        if len(missing_fields) > 0:
            raise AlmException('The following fields are missing values: %s' % ', '.join(missing_fields))
        
    def has_field(self, field_name):
        if not self.fields:
            return False
             
        return field_name in self.fields
        
    def get_issue_types(self):
        try:
            return self.call_api('issuetype')
        except APIError, error:
            raise AlmException('Unable to get issuetype from JIRA API. %s' % error)

    def get_subtask_issue_types(self):
        return self.get_issue_types()

    def get_task(self, task, task_id):

        task_lookup = []
        task_lookup.append('summary~\'%s\'' % self.urlencode_str(task['alm_fixed_title']))

        for field_data in self.custom_lookup_fields:

            # clauseNames is a list of JQL field name aliases. We only need one
            field_clause = field_data['meta']['clauseNames'][0]
            field_meta = field_data['meta']
            field_value = field_data['value']

            if isinstance(field_value, list):
                for list_item in field_value:
                    condition = '%s=\'%s\'' % (field_clause, self.urlencode_str(list_item))
                    task_lookup.append(condition)
            else:
                if field_meta['schema']['type'] == 'string':
                    condition = '%s~\'%s\'' % (field_clause, self.urlencode_str(field_value))
                else:
                    condition = '%s=\'%s\'' % (field_clause, self.urlencode_str(field_value))
                task_lookup.append(condition)

        try:
            url = 'search?jql=project%%3D\'%s\'%%20AND%%20%s' % (self.config['alm_project'],
                                                                 '%20AND%20'.join(task_lookup))
            result = self.call_api(url)
        except APIError, error:
            raise AlmException("Unable to get task %s from JIRA. %s" % (task_id, error))

        if not result['total']:
            # No result was found from query
            return None

        # We will use the first result from the query
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
        except APIError, error:
            raise AlmException('Unable to update issue %s with new version %s. %s' %
                               (task.get_alm_id(), project_version, error))

    def add_task(self, task, issue_type_id, project_version):
        affected_versions = []
        if self.config['alm_project_version']:
            affected_versions.append({'name': self.config['alm_project_version']})

        # Add task
        args = {
            'fields': {
                'project': {
                    'key': self.config['alm_project']
                },
                'summary': task['alm_full_title'],
                'issuetype': {
                    'id': issue_type_id
                },
            }
        }

        # collect task tags
        tags = [self.config['alm_issue_label']] + task['tags']

        if self.has_field('description'):
            args['fields']['description'] = task['formatted_content']

        if self.has_field('reporter'):
            args['fields']['reporter'] = {'name': self.config['alm_user']}

        if self.has_field('labels'):
            args['fields']['labels'] = tags

        if self.has_field('priority'):
            args['fields']['priority'] = {'name': task['alm_priority']}

        if affected_versions:
            args['fields']['versions'] = affected_versions

        if self.config['alm_parent_issue']:
            args['fields']['parent'] = {'key': self.config['alm_parent_issue']}

        unsupported_fields = []

        for field_id, custom_field_value in self.custom_fields.iteritems():

            mapped_field = self.fields[field_id]

            if mapped_field['schema']['type'] == 'array' and mapped_field['schema']['items'] == 'string':
                # Expand on what we already have defined above
                if field_id in args['fields'] and isinstance(args['fields'][field_id], list):
                    field_values = args['fields'][field_id]
                else:
                    field_values = []

                # Accommodate more than one custom field value in this field
                if isinstance(custom_field_value, list):
                    for list_item in custom_field_value:
                        field_values.append(list_item)
                else:
                    field_values.append(custom_field_value)
                args['fields'][field_id] = field_values
            elif mapped_field['schema']['type'] == 'array' and mapped_field['schema']['items'] == 'component':
                if isinstance(custom_field_value, list):
                    field_values = []
                    for list_item in custom_field_value:
                        field_values.append({'name': list_item})
                    args['fields'][field_id] = field_values
                else:
                    args['fields'][field_id] = [{'name': custom_field_value}]
            elif mapped_field['schema']['type'] == 'string':
                if 'allowedValues' in mapped_field:
                    args['fields'][field_id] = {'value': custom_field_value}
                else:
                    args['fields'][field_id] = custom_field_value
            elif mapped_field['required']:
                unsupported_fields.append(mapped_field['name'])

        if len(unsupported_fields) > 0:
            raise AlmException('Unable to add issue due to unsupported fields: %s' % ', '.join(unsupported_fields))

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
        except APIError, error:
            raise AlmException("Unable to get transition IDS for JIRA task %s. %s" % (task_id, error))
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
