# Copyright SDElements Inc
# Extensible two way integration with PivotalTracker

import re
from datetime import datetime
from types import ListType

from sdetools.sdelib.commons import urlencode_str
from sdetools.sdelib.restclient import RESTBase
from sdetools.sdelib.restclient import URLRequest, APIError
from sdetools.alm_integration.alm_plugin_base import AlmTask, AlmConnector
from sdetools.alm_integration.alm_plugin_base import AlmException

from sdetools.sdelib import log_mgr
logger = log_mgr.mods.add_mod(__name__)

RE_MAP_RANGE_KEY = re.compile('^\d+(-\d+)?$')
PT_DEFAULT_PRIORITY_MAP = {
    '7-10': 'High',
    '4-6': 'Medium',
    '1-3': 'Low',
    }
PUBLIC_TASK_CONTENT = 'Visit us at http://www.sdelements.com/ to find out how you can easily add project-specific '\
                      'software security requirements to your existing development processes.'


class PivotalTrackerAPI(RESTBase):
    """ Base plugin for PivotalTracker """

    def __init__(self, config):
        extra_conf_opts = [('alm_api_token', 'PivotalTracker API Token', '')]
        super(PivotalTrackerAPI, self).__init__('alm', 'PivotalTracker', config, 'services/v5', extra_conf_opts)

    def post_conf_init(self):
        if self._get_conf('api_token'):
                self.set_auth_mode('api_token')
                self.api_token_header_name = 'X-TrackerToken'
                self.config[self._get_conf_name('pass')] = self._get_conf('api_token')

        super(PivotalTrackerAPI, self).post_conf_init()

    def parse_response(self, result, headers):
        if result == "":
            return "{}"
        else:
            return super(PivotalTrackerAPI, self).parse_response(result, headers)


class PivotalTrackerTask(AlmTask):
    """ Representation of a task in PivotalTracker """

    def __init__(self, task_id, alm_id, status, timestamp, done_statuses, updateable):
        self.task_id = task_id
        self.alm_id = alm_id
        self.status = status
        self.timestamp = timestamp
        self.done_statuses = done_statuses  # comma-separated list
        self.priority = None
        self.updateable = updateable

    def get_task_id(self):
        return self.task_id

    def get_alm_id(self):
        return self.alm_id

    def get_status(self):
        """ Translates PivotalTracker status into SDE status """
        if self.status in self.done_statuses:
            return 'DONE'
        else:
            return 'TODO'

    def get_timestamp(self):
        """ Returns a datetime object """
        return datetime.strptime(self.timestamp, '%Y-%m-%dT%H:%M:%SZ')

    def is_updateable(self):
        """
        The task is updateable from SDE to ALM if the story does not require estimates
        or it does require estimates and has an estimate. False otherwise
        """
        return self.updateable


class PivotalTrackerConnector(AlmConnector):
    alm_name = 'PivotalTracker'
    PT_STORY_TYPE = 'pt_story_type'
    ALM_NEW_STATUS = 'pt_new_status'
    ALM_DONE_STATUSES = 'pt_done_statuses'
    ALM_PROJECT_VERSION = 'alm_project_version'
    ALM_PRIORITY_MAP = 'alm_priority_map'
    PT_GROUP_LABEL = 'pt_group_label'
    PT_VALID_STORY_TYPES = ['feature', 'bug', 'chore']
    PT_VALID_DONE_STATUSES = ['accepted', 'delivered', 'finished']
    PT_VALID_NEW_STATUSES = ['unstarted', 'unscheduled', 'started']
    PT_DEFAULT_ESTIMATE = 'pt_default_estimate'

    def __init__(self, config, alm_plugin):
        """ Initializes connection to PivotalTracker """
        super(PivotalTrackerConnector, self).__init__(config, alm_plugin)

        config.opts.add(self.PT_STORY_TYPE, 'Default story type on PivotalTracker', default='bug')
        config.opts.add(self.ALM_NEW_STATUS, 'Status to set for new tasks in PivotalTracker',
                                 default='unscheduled')
        config.opts.add(self.ALM_DONE_STATUSES, 'Statuses that signify a task is Done in PivotalTracker',
                                 default='accepted')
        config.opts.add(self.ALM_PROJECT_VERSION, 'Name of release marker to place all new stories under',
                                 default='')
        config.opts.add(self.ALM_PRIORITY_MAP, 'Customized priority mapping from SDE to PivotalTracker '
                                 '(JSON encoded dictionary of strings)', default='')
        config.opts.add(self.PT_GROUP_LABEL, 'PivotalTracker label for issues generated by SD Elements',
                                 default='SD Elements')
        config.opts.add(self.PT_DEFAULT_ESTIMATE, 'Default estimate to use when closing unestimated stories',
                                 default='')
        self.alm_task_title_prefix = 'SDE '
        self.sync_titles_only = True
        self.pt_epic_exist = None
        self.requires_estimate = ['feature']    # by default only features require an estimate
        self.pt_point_scale = []

    def initialize(self):
        super(PivotalTrackerConnector, self).initialize()

        # Verify that the configuration options are set properly
        for item in [self.ALM_NEW_STATUS, self.ALM_DONE_STATUSES, self.PT_STORY_TYPE]:
            if not self.config[item]:
                raise AlmException('Missing %s in configuration' % item)

        self.config.process_list_config(self.ALM_DONE_STATUSES)

        self.config.process_json_str_dict('alm_priority_map')
        if not self.config[self.ALM_PRIORITY_MAP]:
            self.config[self.ALM_PRIORITY_MAP] = PT_DEFAULT_PRIORITY_MAP
        self._validate_alm_priority_map()

    def alm_connect_server(self):
        """ Verifies that PivotalTracker connection works """
        # Check if user can successfully authenticate and retrieve user profile
        try:
            user_info = self.alm_plugin.call_api('me')
        except APIError, err:
            raise AlmException('Unable to connect to PivotalTracker service (Check'
                               'server URL, user, pass). Reason: %s' % str(err))

        if user_info.get('error'):
            raise AlmException('Could not authenticate PivotalTracker user %s. Reason: %s' %
                              (self.config['alm_user'], user_info['error']))

    def alm_connect_project(self):
        """ Verifies that the PivotalTracker project exists """
        self.project_uri = None

        # Find the PivotalTracker project
        try:
            projects_list = self.alm_plugin.call_api('projects')
        except APIError, err:
            raise AlmException('Unable to find PivotalTracker project %s. Reason: %s' %
                              (self.config['alm_project'], str(err)))

        for project in projects_list:
            if project['name'] == self.config['alm_project']:
                self.project_uri = 'projects/%d' % project['id']
                self.sync_titles_only = project['public']
                if project['bugs_and_chores_are_estimatable']:
                    self.requires_estimate = self.PT_VALID_STORY_TYPES
                self.pt_point_scale = [float(e) for e in project['point_scale'].split(',')]
                if not self.config[self.PT_DEFAULT_ESTIMATE]:
                    # Use the first value as the default value
                    self.config[self.PT_DEFAULT_ESTIMATE] = self.pt_point_scale[0]
                break

        if self.project_uri is None:
            raise AlmException('PivotalTracker project %s is missing or invalid' % self.config['alm_project'])

    def alm_validate_configurations(self):
        """ We have no way of fetching the valid values for each field so we will hard-code them """
        # Validate the default story estimate
        if not self.pt_point_scale:
            raise AlmException('Failed to retrieve estimate point scale from the Pivotal Tracker project')
        try:
            self.config[self.PT_DEFAULT_ESTIMATE] = float(self.config[self.PT_DEFAULT_ESTIMATE])
        except:
            raise AlmException('Expected a numeric value for %s' % self.PT_DEFAULT_ESTIMATE)

        validate_configurations = [
            (self.PT_DEFAULT_ESTIMATE, self.pt_point_scale),
            (self.ALM_NEW_STATUS, self.PT_VALID_NEW_STATUSES),
            (self.ALM_DONE_STATUSES, self.PT_VALID_DONE_STATUSES),
            (self.PT_STORY_TYPE, self.PT_VALID_STORY_TYPES)
        ]

        for conf, valid_values in validate_configurations:
            configured_value = self.config[conf]

            if type(configured_value) != ListType:
                if configured_value not in valid_values:
                    raise AlmException('Invalid %s %s. Expected one of %s.' % (conf, configured_value,  valid_values))
            else:
                difference_set = set(configured_value).difference(valid_values)
                if difference_set:
                    raise AlmException('Invalid %s %s. Expected one of %s.' % (conf, difference_set,  valid_values))

        if self.config[self.PT_STORY_TYPE] == 'chore':
            # Chores only have one applicable completion state - 'accepted'
            if 'accepted' in self.config[self.ALM_DONE_STATUSES]:
                self.config[self.ALM_DONE_STATUSES] = ['accepted']
            else:
                raise AlmException('Chores only have one completion state - "accepted"')

    def alm_remove_task(self, task):
        delete_url = '%s/stories/%s' % (self.project_uri, task.get_alm_id())
        try:
            self.alm_plugin.call_api(delete_url, method=URLRequest.DELETE)
        except APIError, err:
            raise AlmException("Unable to delete task : %s" % err)

    def alm_get_task(self, task):
        task_id = self._extract_task_id(task['id'])
        if not task_id:
            return None

        try:
            # Fields parameter will filter response data to only contain story status, name, timestamp and id
            target = ('%s/stories?filter="%s:"&fields=current_state,name,updated_at,id,estimate,story_type' %
                     (self.project_uri, urlencode_str(task_id)))
            stories = self.alm_plugin.call_api(target)
        except APIError, err:
            logger.error(err)
            raise AlmException('Unable to get story %s from PivotalTracker' % task_id)

        if not stories:
            return None

        story = stories[0]

        if len(stories) > 1:
            logger.warning('Found multiple issues with the title %s. Selecting the first task found with id %s'
                           % (task_id, story['id']))

        logger.info('Found task: %s', task_id)
        updateable = story['story_type'] not in self.requires_estimate or story.get('estimate') is not None

        return PivotalTrackerTask(task_id,
                                  story['id'],
                                  story['current_state'],
                                  story['updated_at'],
                                  self.config[self.ALM_DONE_STATUSES],
                                  updateable)

    def pt_get_release_marker_id(self, release_name):
        try:
            release_markers = self.alm_plugin.call_api('%s/stories?filter=type:release,%s&fields=id' %
                                                       (self.project_uri, urlencode_str(release_name)))
        except APIError, err:
            raise AlmException('Could not find release marker %s in PivotalTracker because of %s'
                               % (release_name, err))

        if not release_markers:
            raise AlmException('Could not find release marker %s in PivotalTracker' % release_name)

        release_marker = release_markers[0]

        if len(release_markers) > 1:
            logger.warning('Found multiple release markers with the title %s. Selecting the first release marker'
                           'found with id %s' % (release_name, release_marker['id']))

        if release_marker.get('error'):
            raise AlmException('Could not find release marker %s in PivotalTracker. Reason: %s - %s'
                               % (release_name, release_marker['code'], release_marker['general_problem']))
        else:
            return release_marker['id']

    def translate_priority(self, priority):
        """ Translates an SDE priority into a PivotalTracker label """
        pmap = self.config[self.ALM_PRIORITY_MAP]

        if not pmap:
            return None

        try:
            priority = int(priority)
        except TypeError:
            logger.error('Could not coerce %s into an integer' % priority)
            raise AlmException("Error in translating SDE priority to PivotalTracker label: "
                               "%s is not an integer priority" % priority)

        for key in pmap:
            if '-' in key:
                lrange, hrange = key.split('-')
                lrange = int(lrange)
                hrange = int(hrange)
                if lrange <= priority <= hrange:
                    return pmap[key]
            else:
                if int(key) == priority:
                    return pmap[key]

    def pt_get_epic(self, group_name):
        try:
            epic = self.alm_plugin.call_api('%s/epics?filter=%s&fields=id' %
                                            (self.project_uri, urlencode_str(group_name)))
        except APIError, err:
            raise AlmException('Unable to get epic %s from PivotalTracker because of %s'
                               % (group_name, err))

        return epic

    def pt_add_epic(self, group_name):
        """
            Related stories in Pivotal Tracker can be grouped together as an 'Epic'.
            We will group all stories we create under the same label and epic.
        """
        create_args = {
            'name': group_name,
            'description': 'Auto-generated by SD Elements',
            'label': {"name": group_name},
        }

        try:
            self.alm_plugin.call_api('%s/epics' % self.project_uri,
                                     method=self.alm_plugin.URLRequest.POST,
                                     args=create_args)
            logger.debug('Epic %s added to PivotalTracker Project', group_name)
        except APIError, err:
            raise AlmException('Unable to add epic %s to PivotalTracker because of %s'
                               % (group_name, err))

    def alm_add_task(self, task):
        pt_priority_label = self.translate_priority(task['priority'])
        pt_release_marker_name = self.config[self.ALM_PROJECT_VERSION]
        pt_group_label = self.config[self.PT_GROUP_LABEL]
        pt_labels = []
        task_content = PUBLIC_TASK_CONTENT

        if not self.sync_titles_only:
            task_content = self.sde_get_task_content(task)

        create_args = {
            'name': task['title'],
            'description': task_content,
            'current_state': self.config[self.ALM_NEW_STATUS],
            'story_type': self.config[self.PT_STORY_TYPE],
        }
        if create_args['story_type'] in self.requires_estimate:
            create_args['estimate'] = self.config[self.PT_DEFAULT_ESTIMATE]
        if pt_priority_label:
            pt_labels.append({'name': pt_priority_label})
        if pt_release_marker_name:
            create_args['after_id'] = self.pt_get_release_marker_id(pt_release_marker_name)
        if pt_group_label:
            # Using a boolean variable to prevent redundant api calls
            if self.pt_epic_exist is None:
                self.pt_epic_exist = self.pt_get_epic(pt_group_label)
            if not self.pt_epic_exist:
                self.pt_add_epic(pt_group_label)
                self.pt_epic_exist = True

            pt_labels.append({'name': pt_group_label})
        if pt_labels:
            create_args['labels'] = pt_labels

        try:
            new_story = self.alm_plugin.call_api('%s/stories' % self.project_uri,
                                                 method=self.alm_plugin.URLRequest.POST,
                                                 args=create_args)
            logger.debug('Story %s added to PivotalTracker', task['id'])
        except APIError, err:
            raise AlmException('Unable to add story %s to PivotalTracker because of %s'
                               % (task['id'], err))

        if new_story.get('error'):
            raise AlmException('Unable to add story %s to PivotalTracker. Reason: %s - %s'
                               % (task['id'], new_story['code'], new_story['general_problem']))

        updateable = new_story['story_type'] not in self.requires_estimate or new_story.get('estimate') is not None
        # API returns JSON of the new issue
        alm_task = PivotalTrackerTask(task['title'],
                                      new_story['id'],
                                      new_story['current_state'],
                                      new_story['updated_at'],
                                      self.config[self.ALM_DONE_STATUSES],
                                      updateable)

        if (self.config['alm_standard_workflow'] and
                (task['status'] == 'DONE' or task['status'] == 'NA')):
            self.alm_update_task_status(alm_task, task['status'])

        return 'Project: %s, Story: %s' % (self.config['alm_project'], alm_task.get_alm_id())

    def alm_update_task_status(self, task, status):
        if not task or not self.config['alm_standard_workflow']:
            logger.debug('Status synchronization disabled')
            return

        alm_state = None

        if status == 'DONE' or status == 'NA':
            alm_state = self.config[self.ALM_DONE_STATUSES][0]
        elif status == 'TODO':
            alm_state = self.config[self.ALM_NEW_STATUS]

        pt_release_marker_name = self.config[self.ALM_PROJECT_VERSION]
        update_args = {
            'current_state': alm_state
        }
        if not task.is_updateable():
            update_args['estimate'] = self.config[self.PT_DEFAULT_ESTIMATE]
        if pt_release_marker_name:
            update_args['after_id'] = self.pt_get_release_marker_id(pt_release_marker_name)
        try:
            result = self.alm_plugin.call_api('%s/stories/%s' % (self.project_uri, task.get_alm_id()),
                                              args=update_args, method=URLRequest.PUT)
        except APIError, err:
            raise AlmException('Unable to update story status to %s '
                               'for story %s in PivotalTracker because of %s' %
                               (status, task.get_alm_id(), err))

        if result and result.get('error'):
            raise AlmException('Unable to update status to %s for story %s. Reason: %s - %s' %
                               (status, task['id'], result['code'], result['general_problem']))

        logger.debug('Status changed to %s for story %s in PivotalTracker' %
                     (status, task.get_alm_id()))

    def alm_disconnect(self):
        pass

    def convert_markdown_to_alm(self, content, ref):
        markdown_urls = re.findall('\[[^\]]+\]\([^\)]+\)', content)
        if markdown_urls:
            for markdown_url in markdown_urls:
                url_search = re.search('\[([^\]]+)\]\(([^\)]+)\)', markdown_url)
                if url_search:
                    if url_search.group(1) == url_search.group(2):
                        content = content.replace('[' + url_search.group(1) + '](' + url_search.group(2) + ')',
                                                  url_search.group(1))
                    else:
                        content = content.replace('[' + url_search.group(1) + '](' + url_search.group(2) + ')',
                                                  url_search.group(1) + ": " + url_search.group(2))
        return content
