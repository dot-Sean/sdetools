# Copyright SDElements Inc
# Extensible two way integration with Rally

import sys
import re
from datetime import datetime

from sdetools.sdelib.restclient import RESTBase, APIError
from sdetools.alm_integration.alm_plugin_base import AlmTask, AlmConnector
from sdetools.alm_integration.alm_plugin_base import AlmException
from sdetools.extlib import markdown

from sdetools.sdelib import log_mgr
logger = log_mgr.mods.add_mod(__name__)

API_VERSION = '1.39'

MAX_CONTENT_SIZE = 30000

RALLY_HEADERS = [
    ('X-RallyIntegrationName', 'SD Elements'),
    ('X-RallyIntegrationVendor', 'SD Elements'),
    ('X-RallyIntegrationVersion', '1.0'),
    ('X-RallyIntegrationOS', sys.platform),
    ('X-RallyIntegrationPlatform', 'Python %s' % sys.version.split(' ', 1)[0].replace('\n', '')),
    ('X-RallyIntegrationLibrary', 'Rally REST API'),
]

RALLY_HTML_CONVERT = [
    ('<h1>', '<br><font size="5">'),
    ('<h2>', '<br><font size="4">'),
    ('<h3>', '<br><font size="3">'),
    ('<h4>', '<br><font size="2">'),
    ('<h5>', '<br><font size="2">'),
    ('<h6>', '<br><font size="2">'),
    (re.compile('</h[1-6]>'), '</font><br><br>'),
    ('<p>', ''),
    ('</p>', '<br><br>'),
    ('<pre><code>', '<span style="font-family: courier new,monospace;"><pre><code>'),
    ('</code></pre>', '</code></pre></span>'),
]


class RallyAPIBase(RESTBase):
    """ Base plugin for Rally """

    def __init__(self, config):
        super(RallyAPIBase, self).__init__('alm', 'Rally', config, 'slm/webservice/%s' % API_VERSION)

    def get_custom_headers(self, target, method):
        return RALLY_HEADERS


class RallyTask(AlmTask):
    """ Representation of a task in Rally """

    def __init__(self, task_id, alm_id, alm_task_ref, status, timestamp, done_statuses):
        self.task_id = task_id
        self.alm_id = alm_id

        #A Reference URL to the task in Rally
        self.alm_task_ref = alm_task_ref
        self.status = status
        self.timestamp = timestamp
        self.done_statuses = done_statuses  # comma-separated list

    def get_task_id(self):
        return self.task_id

    def get_alm_task_ref(self):
        return self.alm_task_ref

    def get_alm_id(self):
        return self.alm_id

    def get_status(self):
        """Translates Rally status into SDE status"""
        if self.status in self.done_statuses:
            return 'DONE'
        else:
            return 'TODO'

    def get_timestamp(self):
        """ Returns a datetime object """
        return datetime.strptime(self.timestamp, '%Y-%m-%dT%H:%M:%S.%fZ')


class RallyConnector(AlmConnector):
    """Connects SD Elements to Rally"""
    alm_name = 'Rally'
    feature_custom_lookup = True

    def __init__(self, config, alm_plugin):
        super(RallyConnector, self).__init__(config, alm_plugin)

        """ Adds Rally specific config options to the config file"""
        config.opts.add('rally_new_status', 'status to set for new tasks in Rally',
                                 default='Defined')
        config.opts.add('rally_done_statuses', 'Statuses that signify a task is Done in Rally',
                                 default='Completed,Accepted')
        config.opts.add('rally_workspace', 'Rally Workspace', default=None)
        config.opts.add('rally_card_type', 'IDs for issues raised in Rally', default='Story')
        config.opts.add('alm_issue_label', 'Label applied to issue in Rally', default='SD-Elements')
        config.opts.add('alm_parent_issue', 'Parent Story for new Tasks', default='')

        self.tag_references = {}
        self.card_types = {}
        self.project_ref = None
        self.workspace_ref = None
        self.alm_parent_issue_ref = None
        self.tag_ref = None
        self.mark_down_converter = markdown.Markdown(safe_mode="escape")

    def initialize(self):
        super(RallyConnector, self).initialize()

        # Verify that the configuration options are set properly
        for item in ['rally_done_statuses',
                     'rally_card_type',
                     'rally_new_status',
                     'rally_workspace',
                     'alm_issue_label']:

            if not self.config[item]:
                raise AlmException('Missing %s in configuration' % item)

        self.config.process_list_config('rally_done_statuses')

        self.card_types = {
            'Story': {
                'name': 'Story',
                'type': 'HierarchicalRequirement',
                'query': 'Hierarchical Requirement',
                'api': 'hierarchicalrequirement',
                'field_state': 'ScheduleState',
                'requires_parent': False,
                'url_component_name': 'userstory',
                'field_validation_state': 'Schedule State'
            },
            'Task': {
                'name': 'Task',
                'type': 'Task',
                'query': 'Task',
                'api': 'task',
                'field_state': 'State',
                'requires_parent': True,
                'url_component_name': 'task',
                'field_validation_state': 'State'
            }
        }

        # Sanity-check alm_parent_issue
        if self.config['alm_parent_issue'] and self.config['rally_card_type'] != 'Task':
            raise AlmException('Option alm_parent_issue is only valid if rally_card_type is Task')
        if self.config['rally_card_type'] == 'Task' and not self.config['alm_parent_issue']:
            raise AlmException('Missing alm_parent_issue in configuration')

    def carriage_return(self):
        return '<br//>'

    def _get_issue_url(self, alm_task):

        card_type_details = self.card_types[self.config['rally_card_type']]

        return "%s://%s/#%sd/detail/%s%s" % (
            self.config['alm_method'],
            self.config['alm_server'],
            self.project_ref[self.project_ref.rfind('/'):self.project_ref.rfind('.')],
            card_type_details['url_component_name'],
            alm_task.alm_task_ref[alm_task.get_alm_task_ref().rfind('/'):alm_task.get_alm_task_ref().rfind('.')],
        )

    def alm_connect_server(self):
        """ Verifies that Rally connection works """
        # Check to make sure that we can do a simple API call
        try:
            self.alm_plugin.call_api('task.js')
        except APIError, err:
            raise AlmException('Unable to connect to Rally service (Check server URL, user, pass). Reason: %s'
                               % str(err))

    def alm_connect_project(self):
        workspace_ref = None

        # Now try to get workspace ID
        try:
            subscription_ref = self.alm_plugin.call_api('subscription.js')
        except APIError, err:
            raise AlmException('Unable to retrieve subscription from Rally. Reason: %s' % err)

        for workspace in subscription_ref['Subscription']['Workspaces']:
            if workspace['_refObjectName'] == self.config['rally_workspace']:
                workspace_ref = workspace['_ref']
                break

        if not workspace_ref:
            raise AlmException('Workspace is not valid, please check config value: %s' % self.config['rally_workspace'])
        self.workspace_ref = workspace_ref

        # Now get project ID
        query_args = {
            'query': '(Name = \"%s\")' % self.config['alm_project'],
            'workspace': self.workspace_ref,
        }
        try:
            project_ref = self.alm_plugin.call_api('project.js', args=query_args)
        except APIError, err:
            raise AlmException('Unable to retrieve project info from Rally. Reason: %s' % err)
        num_results = project_ref['QueryResult']['TotalResultCount']
        if not num_results:
            raise AlmException('Rally project not found: %s' % self.config['alm_project'])
        self.project_ref = project_ref['QueryResult']['Results'][0]['_ref']

    def _setup_rally_label(self, tag_name):

        # Find the issue tag
        query_args = {
            'query': '(Name = \"%s\")' % tag_name,
            'workspace': self.workspace_ref,
        }
        try:
            tag_result = self.alm_plugin.call_api('tag.js', args=query_args)
        except APIError, err:
            raise AlmException('Unable to retrieve tag info from Rally. Reason: %s' % err)

        num_results = tag_result['QueryResult']['TotalResultCount']
        if num_results:
            self.tag_references[tag_name] = tag_result['QueryResult']['Results'][0]['_ref']
            return

        create_args = {
            'Tag': {
                'Name': tag_name,
                'Workspace': self.workspace_ref,
            }
        }

        try:
            tag_result = self.alm_plugin.call_api(
                'tag/create.js',
                args=create_args,
                method=self.alm_plugin.URLRequest.POST)
        except APIError, err:
            raise AlmException('Unable to create tag info from Rally. Reason: %s' % err)

        if tag_result['CreateResult']['Errors']:
            raise AlmException('Unable to add label "%s" to Rally. Reason: %s' %
                              (tag_name, str(tag_result['CreateResult']['Errors'])[:200]))

        self.tag_references[tag_name] = tag_result['CreateResult']['Object']['_ref']

    def alm_validate_configurations(self):

        # Retrieve the reference for the parent Story
        if self.config['alm_parent_issue']:
            rally_artifact = self.rally_get_artifact(
                self.config['alm_parent_issue'],
                '(FormattedID = \"%s\")' % self.config['alm_parent_issue'],
                'Story',
                'HierarchicalRequirement',
                'hierarchicalrequirement'
            )

            if rally_artifact and 'FormattedID' in rally_artifact:
                self.alm_parent_issue_ref = rally_artifact['_ref']

            if not self.alm_parent_issue_ref:
                raise AlmException('Could not retrieve reference for %s' % self.config['alm_parent_issue'])

        if self.config['rally_card_type'] not in self.card_types.keys():
            raise AlmException("Invalid configuration for rally_card_type \"%s\". Expected one of %s" %
                               (self.config['rally_card_type'], ', '.join(self.card_types.keys())))

        card_type_details = self.card_types[self.config['rally_card_type']]

        query_args = {
            'query': '(Name = \"%s\")' % card_type_details['query'],
            'workspace': self.workspace_ref,
        }

        try:
            requirement_definition = self.alm_plugin.call_api('typedefinition.js', args=query_args)
        except APIError, err:
            raise AlmException('Error while querying type definition for "%s": %s' % (card_type_details['type'], err))
        except (KeyError, IndexError):
            raise AlmException('Failed to retrieve type definition for "%s"' % card_type_details['type'])

        requirement_definition_ref = requirement_definition['QueryResult']['Results'][0]['_ref']

        try:
            requirement_attrs = self.alm_plugin.call_api(self._split_ref_link(requirement_definition_ref))
        except APIError, err:
            raise AlmException('Error while retrieving attribute definitions for "%s": %s' %
                               (err, card_type_details['type']))

        for attribute in requirement_attrs['TypeDefinition']['Attributes']:
            if attribute['Name'] == card_type_details['field_validation_state']:
                allowed_values = [v['StringValue'] for v in attribute['AllowedValues']]

                if self.config['rally_new_status'] not in allowed_values:
                    raise AlmException('Invalid rally_new_status "%s". Expected one of %s' %
                                       (self.config['rally_new_status'], allowed_values))

                difference_set = set(self.config['rally_done_statuses']).difference(allowed_values)
                if difference_set:
                    raise AlmException('Invalid rally_done_statuses %s. Expected one of %s' %
                                       (difference_set, allowed_values))
                return
        raise AlmException('Unable to retrieve allowed values for "%s"' % card_type_details['name'])

    def rally_get_artifact(self, name, query, card_type, artifact_type, api):

        query_args = {
            'query': query,
            'workspace': self.workspace_ref,
            'project': self.project_ref,
        }

        try:
            result = self.alm_plugin.call_api('%s.js' % api, args=query_args)
        except APIError, err:
            raise AlmException('Unable to get %s %s from Rally. Reason: %s' % (card_type, name, str(err)))
        num_results = result['QueryResult']['TotalResultCount']

        if not num_results:
            return None

        task_result_url = self._split_ref_link(result['QueryResult']['Results'][0]['_ref'])
        try:
            task_data = self.alm_plugin.call_api(task_result_url)
        except APIError, err:
            raise AlmException('Unable to get artifact from Rally. Reason: %s' % (str(err)))
        return task_data[artifact_type]

    def _apply_labels_if_needed(self, labels, artifact_data):
        if 'Tags' not in artifact_data:
            artifact_data['Tags'] = []

        # Determine which tags are missing
        for tag in artifact_data['Tags']:
            if '_refObjectName' in tag and tag['_refObjectName'] in labels:
                labels.remove(tag['_refObjectName'])

        # The Rally artifact is assigned all tags
        if not labels:
            return

        card_type_details = self.card_types[self.config['rally_card_type']]

        # Get or create the missing tags if needed
        for tag_name in labels:
            if tag_name not in self.tag_references:
                self._setup_rally_label(tag_name)
            artifact_data['Tags'].append({'_ref': self.tag_references[tag_name]})

        tag_update = {
            card_type_details['type']: {
                'Tags': artifact_data['Tags'],
            }
        }

        artifact_id = self._split_ref_link(artifact_data['_ref'])
        try:
            self.alm_plugin.call_api(artifact_id, args=tag_update, method=self.alm_plugin.URLRequest.POST)
        except APIError, err:
            raise AlmException('Unable to update tag %s for artifact %s in Rally because of %s' %
                               (tag_name, artifact_data['FormattedID'], err))

    def alm_get_task(self, task):
        card_type_details = self.card_types[self.config['rally_card_type']]
        task_id = self._extract_task_id(task['id'])

        artifact_query = '(Name contains "%s")' % task['alm_fixed_title']

        if card_type_details['type'] == 'Task':
            artifact_query = '(%s and (WorkProduct.FormattedID = "%s"))' % (
                             artifact_query, self.config['alm_parent_issue'])

        for field, value in self.config['alm_custom_lookup_fields'].items():
            artifact_query = '(%s and (%s = "%s"))' % (artifact_query, field, value)

        task_data = self.rally_get_artifact(task_id, '%s' % artifact_query, card_type_details['type'],
                                            card_type_details['type'], card_type_details['api'])
        if not task_data:
            return task_data

        # Make sure the artifact has all the applicable labels
        tags = [self.config['alm_issue_label']] + task['tags']
        self._apply_labels_if_needed(tags, task_data)

        return RallyTask(task_id,
                         task_data['FormattedID'],
                         self._split_ref_link(task_data['_ref']),
                         task_data[card_type_details['field_state']],
                         task_data['LastUpdateDate'],
                         self.config['rally_done_statuses'])

    def alm_add_task(self, task):
        card_type_details = self.card_types[self.config['rally_card_type']]

        create_args = {
            card_type_details['type']: {
                'Name': task['alm_full_title'],
                'Description': self.sde_get_task_content(task),
                'Workspace': self.workspace_ref,
                'Project': self.project_ref
            }
        }

        # Setup labels
        create_args[card_type_details['type']]['Tags'] = []

        labels = [self.config['alm_issue_label']] + task['tags']
        for label in labels:
            if label not in self.tag_references:
                self._setup_rally_label(label)
            create_args[card_type_details['type']]['Tags'].append({'_ref': self.tag_references[label]})

        # Setup parent issue if applicable
        if card_type_details['type'] == 'Task':
            create_args[card_type_details['type']]['WorkProduct'] = self.alm_parent_issue_ref

        # Setup custom fields if necessary
        if self.config['alm_custom_fields']:
            for key in self.config['alm_custom_fields']:
                create_args[card_type_details['type']][key] = self.config['alm_custom_fields'][key]

        try:
            result = self.alm_plugin.call_api('%s/create.js' % card_type_details['api'],
                                              method=self.alm_plugin.URLRequest.POST, args=create_args)
        except APIError, err:
            raise AlmException('Unable to add task to Rally %s because of %s' %
                               (task['id'], err))

        logger.debug('Task %s added to Rally Project', task['id'])

        if result['CreateResult']['Errors']:
            raise AlmException('Unable to add task to Rally %s. Reason: %s' %
                               (task['id'], str(result['CreateResult']['Errors'])[:200]))

        # Return a unique identifier to this task in Rally
        logger.info('Getting task %s', task['id'])
        alm_task = self.alm_get_task(task)
        if not alm_task:
            raise AlmException('Alm task not added successfully. Please '
                               'check ALM-specific settings in config file')

        if (self.config['alm_standard_workflow'] and
                (task['status'] == 'DONE' or task['status'] == 'NA')):
            self.alm_update_task_status(alm_task, task['status'])

        return 'Project: %s, %s: %s; URL: %s' % (
            self.config['alm_project'],
            card_type_details['name'],
            alm_task.get_alm_id(),
            self._get_issue_url(alm_task)
        )

    def alm_remove_task(self, task):
        try:
            self.alm_plugin.call_api(task.get_alm_task_ref(), method=self.alm_plugin.URLRequest.DELETE)
        except APIError, err:
            raise AlmException("Unable to delete task: %s" % err)

    def alm_update_task_status(self, task, status):
        if not task:
            logger.debug('Status synchronization disabled')
            return

        card_type_details = self.card_types[self.config['rally_card_type']]

        if status == 'DONE' or status == 'NA':
            schedule_state = self.config['rally_done_statuses'][0]
            status = 'DONE'
        elif status == 'TODO':
            schedule_state = self.config['rally_new_status']
        else:
            raise AlmException('Invalid status %s' % status)

        trans_args = {
            card_type_details['type']: {
                card_type_details['field_state']: schedule_state
            }
        }

        try:
            self.alm_plugin.call_api(task.get_alm_task_ref(), args=trans_args, method=self.alm_plugin.URLRequest.POST)
        except APIError, err:
            raise AlmException('Unable to update task status to %s for artifact %s in Rally because of %s' %
                               (status, task.get_alm_id(), err))

        logger.debug('Status changed to %s for task %s in Rally' % (status, task.get_alm_id()))

    def alm_disconnect(self):
        pass

    def convert_markdown_to_alm(self, content, ref):
        s = self.mark_down_converter.convert(content)

        # We do some jumping through hoops to add <br> at end of each
        # line for segments between code tags
        sliced = s.split('<code>')
        s = [sliced[0]]
        for item in sliced[1:]:
            item = item.split('</code>')
            item[0] = item[0].replace('\n', '<br>\n')
            s.append('</code>'.join(item))
        s = '<code>'.join(s)

        for before, after in RALLY_HTML_CONVERT:
            if type(before) is str:
                s = s.replace(before, after)
            else:
                s = before.sub(after, s)

        if len(s) > MAX_CONTENT_SIZE:
            logger.warning('Content too long for %s - Truncating.' % ref)
            s = s[:MAX_CONTENT_SIZE]

        return s

    @staticmethod
    def _split_ref_link(ref):
        return ref.split('/%s/' % API_VERSION)[1]
