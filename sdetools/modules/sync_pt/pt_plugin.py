# Copyright SDElements Inc
# Extensible two way integration with PivotalTracker

import re
from datetime import datetime

from sdetools.sdelib.commons import urlencode_str
from sdetools.sdelib.restclient import RESTBase
from sdetools.sdelib.restclient import URLRequest, APIError
from sdetools.alm_integration.alm_plugin_base import AlmTask, AlmConnector
from sdetools.alm_integration.alm_plugin_base import AlmException

from sdetools.sdelib import log_mgr
logger = log_mgr.mods.add_mod(__name__)

RE_MAP_RANGE_KEY = re.compile('^\d+(-\d+)?$')


class PivotalTrackerAPI(RESTBase):
    """ Base plugin for PivotalTracker """
    API_TOKEN_HEADER = 'X-TrackerToken'
    PT_API_VERSION = 'pt_api_version'

    def __init__(self, config):
        super(PivotalTrackerAPI, self).__init__('alm', 'PivotalTracker', config, 'services')
        self.auth_mode = 'api_token'
        config.add_custom_option(self.PT_API_VERSION, 'PivotalTracker API version', default='v5')

    def post_conf_init(self):
        super(PivotalTrackerAPI, self).post_conf_init()
        if not self.config[self.PT_API_VERSION]:
            self.config[self.PT_API_VERSION] = 'v5'

        self.base_uri = '%s/%s' % (self.base_uri, self.config[self.PT_API_VERSION])


class PivotalTrackerTask(AlmTask):
    """ Representation of a task in PivotalTracker"""

    def __init__(self, task_id, alm_id, status, timestamp, done_statuses):
        self.task_id = task_id
        self.alm_id = alm_id
        self.status = status
        self.timestamp = timestamp
        self.done_statuses = done_statuses  # comma-separated list

    def get_task_id(self):
        return self.task_id

    def get_alm_id(self):
        return self.alm_id

    def get_priority(self):
        return self.priority

    def get_status(self):
        """ Translates PivotalTracker status into SDE status """
        if self.status in self.done_statuses:
            return 'DONE'
        else:
            return 'TODO'

    def get_timestamp(self):
        """ Returns a datetime object """
        return datetime.strptime(self.timestamp, '%Y-%m-%dT%H:%M:%SZ')


class PivotalTrackerConnector(AlmConnector):
    alm_name = 'PivotalTracker'
    PT_STORY_TYPE = 'pt_story_type'
    ALM_NEW_STATUS = 'pt_new_status'
    ALM_DONE_STATUSES = 'pt_done_statuses'
    PT_API_TOKEN = ''
    ALM_PROJECT_VERSION = 'alm_project_version'
    ALM_PRIORITY_MAP = 'alm_priority_map'

    def __init__(self, config, alm_plugin):
        """ Initializes connection to PivotalTracker """
        super(PivotalTrackerConnector, self).__init__(config, alm_plugin)

        config.add_custom_option(self.PT_STORY_TYPE, 'Default story type on PivotalTracker', default='bug')
        config.add_custom_option(self.ALM_NEW_STATUS, 'Status to set for new tasks in PivotalTracker',
                                 default='open')
        config.add_custom_option(self.ALM_DONE_STATUSES, 'Statuses that signify a task is Done in PivotalTracker',
                                 default='closed')
        config.add_custom_option(self.ALM_PROJECT_VERSION, 'Name of release marker to place all new stories under',
                                 default='')
        config.add_custom_option(self.ALM_PRIORITY_MAP, 'Customized map from priority in SDE to GITHUB '
                                 '(JSON encoded dictionary of strings)', default='')
        self.alm_task_title_prefix = 'SDE '

    def initialize(self):
        super(PivotalTrackerConnector, self).initialize()

        # Verify that the configuration options are set properly
        for item in [self.ALM_NEW_STATUS, self.ALM_DONE_STATUSES, self.PT_STORY_TYPE]:
            if not self.config[item]:
                raise AlmException('Missing %s in configuration' % item)

        self.config[self.ALM_DONE_STATUSES] = self.config[self.ALM_DONE_STATUSES].split(',')

        if self.config[self.ALM_PRIORITY_MAP]:
            self.config.process_json_str_dict(self.ALM_PRIORITY_MAP)

            for key in self.config[self.ALM_PRIORITY_MAP]:
                if not RE_MAP_RANGE_KEY.match(key):
                    raise AlmException('Unable to process %s (not a JSON dictionary). Reason: Invalid range key %s'
                                       % (self.ALM_PRIORITY_MAP, key))

    def alm_connect_server(self):
        """ Verifies that PivotalTracker connection works """
        # Check if user can successfully authenticate and retrieve user profile
        try:
            user_info = self.alm_plugin.call_api('me')
        except APIError, err:
            raise AlmException('Unable to connect to PivotalTracker service (Check'
                               'server URL, user, pass). Reason: %s' % str(err))

        if user_info.get('error'):
            raise AlmException('Could not authenticate PivotalTracker user %s: %s' %
                              (self.config['alm_user'], user_info['error']))

    def alm_connect_project(self):
        """ Verifies that the PivotalTracker project exists """
        self.project_uri = 'projects/%s' % urlencode_str(self.config['alm_project'])

        # Check if PivotalTracker project is accessible
        try:
            repo_info = self.alm_plugin.call_api(self.project_uri)
        except APIError, err:
            raise AlmException('Unable to find PivotalTracker project. Reason: %s' % err)

        if repo_info.get('error'):
            raise AlmException('Error accessing PivotalTracker project with id %s: %s' %
                               self.config['alm_project'], repo_info['error'])

    def alm_get_task(self, task):
        task_id = task['title']
        # PT search API currently does not support search terms with colons
        search_query = task_id.replace(':', '')

        try:
            # Fields parameter will filter response data to only contain story status, name, timestamp and id
            stories = self.alm_plugin.call_api('%s/stories?filter=%s&fields=current_state,name,updated_at,id' %
                                               (self.project_uri, urlencode_str(search_query)))
        except APIError, err:
            logger.error(err)
            raise AlmException('Unable to get task %s from PivotalTracker' % task_id)

        if (not stories):
            return None

        story = stories[0]

        if len(stories) > 1:
            logger.warning('Found multiple issues with the title %s. Selecting the first task found with id %s'
                           % (task_id, story['id']))

        logger.info('Found task: %s', task_id)
        return PivotalTrackerTask(task_id,
                                  story['id'],
                                  story['current_state'],
                                  story['updated_at'],
                                  self.config[self.ALM_DONE_STATUSES])

    def pt_get_release_marker_id(self, release_name):
        try:
            release_markers = self.alm_plugin.call_api('%s/stories?filter=type:release,%s&fields=id' %
                                                       (self.project_uri, urlencode_str(release_name)))
        except APIError, err:
            raise AlmException('Unable to find release marker %s in PivotalTracker because of %s'
                               % (release_name, err))

        if not release_markers:
            raise AlmException('Did not find release marker %s in PivotalTracker')

        release_marker = release_markers[0]

        if len(release_markers) > 1:
            logger.warning('Found multiple release markers with the title %s. Selecting the first release marker'
                           'found with id %s' % (release_name, release_marker['id']))

        if release_marker.get('error'):
            raise AlmException('Unable to find release marker %s in PivotalTracker. Reason: %s - %s'
                               % (release_name, release_marker['code'], release_marker['general_problem']))
        else:
            return release_marker['id']

    def translate_priority(self, priority):
        """ Translates an SDE priority into a GitHub label """
        pmap = self.config[self.ALM_PRIORITY_MAP]

        if not pmap:
            return None

        try:
            priority = int(priority)
        except (TypeError):
            logger.error('Could not coerce %s into an integer' % priority)
            raise AlmException("Error in translating SDE priority to GitHub label: "
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

    def alm_add_task(self, task):
        pt_priority_label = self.translate_priority(task['priority'])
        pt_release_marker_name = self.config[self.ALM_PROJECT_VERSION]

        create_args = {
            'name': task['title'],
            'description': self.sde_get_task_content(task),
            'current_state': self.config[self.ALM_NEW_STATUS],
            'story_type': self.config[self.PT_STORY_TYPE],
        }

        if pt_priority_label:
            create_args['labels'] = [{'name': pt_priority_label}]
        if pt_release_marker_name:
            create_args['after_id'] = self.pt_get_release_marker_id(pt_release_marker_name)

        try:
            new_story = self.alm_plugin.call_api('%s/stories' % self.project_uri,
                                                 method=self.alm_plugin.URLRequest.POST,
                                                 args=create_args)
            logger.debug('Story %s added to PivotalTracker Project', task['id'])
        except APIError, err:
            raise AlmException('Unable to add story %s to PivotalTracker because of %s'
                               % (task['id'], err))

        if new_story.get('error'):
            raise AlmException('Unable to add story %s to PivotalTracker. Reason: %s - %s'
                               % (task['id'], new_story['code'], new_story['general_problem']))

        # API returns JSON of the new issue
        alm_task = PivotalTrackerTask(task['title'],
                                      new_story['id'],
                                      new_story['current_state'],
                                      new_story['updated_at'],
                                      self.config[self.ALM_DONE_STATUSES])

        if (self.config['alm_standard_workflow'] and
                (task['status'] == 'DONE' or task['status'] == 'NA')):
            self.alm_update_task_status(alm_task, task['status'])

        return 'Project: %s, Story: %s' % (self.config['alm_project'], alm_task.get_alm_id())

    def alm_update_task_status(self, task, status):
        if not task or not self.config['alm_standard_workflow']:
            logger.debug('Status synchronization disabled')
            return

        if status == 'DONE' or status == 'NA':
            alm_state = self.config[self.ALM_DONE_STATUSES][0]
        elif status == 'TODO':
            alm_state = self.config[self.ALM_NEW_STATUS]

        pt_release_marker_name = self.config[self.ALM_PROJECT_VERSION]
        update_args = {
            'current_state': alm_state
        }

        if pt_release_marker_name:
            update_args['after_id'] = self.pt_get_release_marker_id(pt_release_marker_name)
        try:
            result = self.alm_plugin.call_api('%s/stories/%s' % (self.project_uri, task.get_alm_id()),
                                              args=update_args, method=URLRequest.PUT)
        except APIError, err:
            raise AlmException('Unable to update task status to %s '
                               'for story: %s in PivotalTracker because of %s' %
                               (status, task.get_alm_id(), err))
        logger.debug('%s' % result)
        if (result and result.get('error')):
            raise AlmException('Unable to update status of task %s to %s. Reason: %s - %s' %
                               (task['id'], status, result['code'], result['general_problem']))

        logger.debug('Status changed to %s for story %s in PivotalTracker' %
                     (status, task.get_alm_id()))

    def alm_disconnect(self):
        pass
