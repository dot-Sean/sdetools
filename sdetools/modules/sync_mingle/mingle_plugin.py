# Copyright SDElements Inc
# Extensible two way integration with Mingle

import urllib
import re
from datetime import datetime
from sdetools.extlib.defusedxml import minidom

from sdetools.sdelib.restclient import RESTBase
from sdetools.sdelib.restclient import URLRequest, APIError
from sdetools.alm_integration.alm_plugin_base import AlmTask, AlmConnector, PUBLIC_TASK_CONTENT
from sdetools.alm_integration.alm_plugin_base import AlmException
from sdetools.extlib import markdown

from sdetools.sdelib import log_mgr
logger = log_mgr.mods.add_mod(__name__)


class MingleAPIBase(RESTBase):
    def __init__(self, config):
        super(MingleAPIBase, self).__init__('alm', 'Mingle', config, 'api/v2')

    def encode_post_args(self, args):
        encoded_args = dict((key.encode('utf-8'), val.encode('utf-8')) for key, val in args.items())
        return urllib.urlencode(encoded_args)

    def parse_response(self, result, headers):
        """ Override's parent return value to include also include the headers """
        if result:
            try:
                result = minidom.parseString(result)
            except Exception:
                # This means that the result doesn't have XML, not an error
                pass
        return headers, result

    def set_content_type(self, req, method):
        pass


class MingleTask(AlmTask):
    """ Representation of a task in Mingle"""

    def __init__(self, task_id, alm_id, status, timestamp, done_statuses):
        self.task_id = task_id
        self.alm_id = alm_id
        self.status = status
        self.timestamp = timestamp
        self.done_statuses = done_statuses  # comma-separated list
        self.priority = None

    def get_task_id(self):
        return self.task_id

    def get_alm_id(self):
        return self.alm_id

    def get_status(self):
        """ Translates Mingle status into SDE status """
        if self.status in self.done_statuses:
            return 'DONE'
        else:
            return 'TODO'

    def get_timestamp(self):
        """ Returns a datetime object """
        return datetime.strptime(self.timestamp,
                                 '%Y-%m-%dT%H:%M:%SZ')


class MingleConnector(AlmConnector):
    alm_name = 'Mingle'

    def __init__(self, config, alm_plugin):
        """ Initializes connection to Mingle """
        super(MingleConnector, self).__init__(config, alm_plugin)

        config.opts.add('mingle_card_type', 'IDs for issues raised in Mingle',
            default='Story')
        config.opts.add('mingle_new_status', 'Status to set for new tasks in Mingle',
            default='Ready for Analysis')
        config.opts.add('mingle_done_statuses', 'Statuses that signify a task is Done in Mingle',
            default='Ready for Testing,In Testing,Ready for Signoff,Accepted')

        self.cached_cards = None
        self.sync_titles_only = True

    def initialize(self):
        super(MingleConnector, self).initialize()

        #Verify that the configuration options are set properly
        for item in ['mingle_done_statuses', 'mingle_card_type', 'mingle_new_status']:
            if not self.config[item]:
                raise AlmException('Missing %s in configuration' % item)

        self.config.process_list_config('mingle_done_statuses')
        self.mark_down_converter = markdown.Markdown(safe_mode="escape")

    def alm_connect_server(self):
        try:
            self.alm_plugin.call_api('projects.xml')
        except APIError, err:
            raise AlmException('Unable to connect to Mingle. Please check server URL, ID, password. Reason: %s' % err)

    def alm_connect_project(self):
        """ Verifies that Mingle connection works """
        self.project_uri = 'projects/%s' % (self.alm_plugin.urlencode_str(self.config['alm_project']))

        #Check to make sure that we can do a simple API call
        try:
            headers, project = self.alm_plugin.call_api('%s.xml' % self.project_uri)
        except APIError, err:
            raise AlmException('Unable to find Mingle project. Reason: %s' % err)

        if self._get_value_of_element_with_tag(project, 'anonymous_accessible') == 'false':
            self.sync_titles_only = False

    def alm_validate_configurations(self):
        # Check if card type is valid
        try:
            headers, result = self.alm_plugin.call_api('%s/card_types.xml' % self.project_uri)
        except APIError, err:
            raise AlmException('Unable to find Mingle card types. Reason: %s' % err)

        types = [self._get_value_of_element_with_tag(t, 'name') for t in result.getElementsByTagName('card_type')]

        if self.config['mingle_card_type'] not in types:
            raise AlmException("The given mingle card type '%s' is not one of the valid card types: %s" %
                               (self.config['mingle_card_type'], ', '.join(types)))

        # Check if new and done statuses are valid
        try:
            headers, result = self.alm_plugin.call_api('%s/property_definitions.xml' % self.project_uri)
        except APIError, err:
            raise AlmException('Unable to retrieve Mingle property definitions. Reason: %s' % err)

        definitions = result.getElementsByTagName('property_definition')
        for definition in definitions:
            if self._get_value_of_element_with_tag(definition, 'name') == 'Status':
                property_id = self._get_value_of_element_with_tag(definition, 'id')

                try:
                    headers, result = self.alm_plugin.call_api('%s/property_definitions/%s.xml' % (self.project_uri, property_id))
                except APIError, err:
                    raise AlmException('Unable to retrieve the Status property definition. Reason: %s' % err)

                property_values = result.getElementsByTagName('property_value')
                statuses = [str(self._get_value_of_element_with_tag(status, 'value')) for status in property_values]

                if self.config['mingle_new_status'] not in statuses:
                    raise AlmException('Invalid mingle_new_status %s. Expected one of %s' %
                                       (self.config['mingle_new_status'], ', '.join(statuses)))

                difference_set = set(self.config['mingle_done_statuses']).difference(statuses)
                if difference_set:
                    raise AlmException('Invalid mingle_done_statuses: %s. Expected one of %s' %
                                      (', '.join(difference_set), ', '.join(statuses)))

                return
        raise AlmException('Could not find the property definition for Status to validate configured statuses')

    def _get_value_of_element_with_tag(self, root, tag_name):
        elements = root.getElementsByTagName(tag_name)

        if elements.length > 0:
            try:
                return elements.item(0).firstChild.nodeValue
            except Exception:
                raise AlmException('Could not get the value of the "%s" element" %s' % tag_name)
        else:
            raise AlmException('Could not find any element with the tag "%s"' % tag_name)

    def _cache_all_sde_mingle_cards(self):
        self.cached_cards = {}

        try:
            headers, result = self.alm_plugin.call_api('%s/cards.xml' % self.project_uri)
        except APIError, err:
            logger.error(err)
            raise AlmException('Unable to get cards from Mingle')

        if result:
            for card_item in result.getElementsByTagName('card'):
                card_name = self._get_value_of_element_with_tag(card_item, 'name')
                card_num = self._get_value_of_element_with_tag(card_item, 'number')
                self.cached_cards[card_num] = card_name

    def _alm_get_task_by_identity(self, identity):
        if not self.cached_cards:
            self._cache_all_sde_mingle_cards()

        card_num = None
        for key in self.cached_cards:
            if self.cached_cards[key].find(identity) >= 0:
                card_num = key
                break

        if card_num is None:
            return None

        try:
            headers, result = self.alm_plugin.call_api('%s/cards/%s.xml' % (self.project_uri, card_num))
            return result
        except APIError:
            raise AlmException('Could not find Mingle card with the card number %s' % card_num)

    def alm_get_task(self, task):
        task_id = self._extract_task_id(task['id'])

        card_item = self._alm_get_task_by_identity(task['alm_fixed_title'])
        if card_item is None:
            return None

        card_num = self._get_value_of_element_with_tag(card_item, 'number')
        modified_date = None
        status = None

        if card_item.getElementsByTagName('modified_on'):
            modified_date = self._get_value_of_element_with_tag(card_item, 'modified_on')
        if card_item.getElementsByTagName('property'):
            properties = card_item.getElementsByTagName('property')

            for prop in properties:
                if self._get_value_of_element_with_tag(prop, 'name') == 'Status':
                    status_node = prop.getElementsByTagName('value').item(0).firstChild

                    if status_node:
                        status = status_node.nodeValue
                    else:
                        status = 'TODO'
                    break

        return MingleTask(task_id, card_num, status, modified_date,
                          self.sde_plugin.config['mingle_done_statuses'])

    def alm_add_task(self, task):
        task_id = self._extract_task_id(task['id'])
        card_name = task['alm_full_title']
        description = PUBLIC_TASK_CONTENT

        if not self.sync_titles_only:
            description = self.sde_get_task_content(task)

        try:
            status_args = {
                'card[name]': card_name,
                'card[card_type_name]': self.sde_plugin.config['mingle_card_type'],
                'card[description]': description,
                'card[properties][][name]': 'status',
                'card[properties][][value]': self.sde_plugin.config['mingle_new_status']
            }
            headers, result = self.alm_plugin.call_api('%s/cards.xml' % self.project_uri, args=status_args,
                                                       method=URLRequest.POST)
            logger.debug('Task %s added to Mingle Project' % task_id)
        except APIError, err:
            raise AlmException('Please check ALM-specific settings in config '
                               'file. Unable to add task %s because of %s' % (task['id'], err))

        # Mingle stores the new card URL in the location header
        card_re = re.search('%s/cards/(\d+).xml' % self.project_uri, headers['location'])
        if card_re:
            if not self.cached_cards:
                self.cached_cards = {}
            self.cached_cards[card_re.group(1)] = task['alm_full_title']
        else:
            raise AlmException('Alm task not added successfully for %s: could not find card number' % task['id'])

        #Return a unique identifier to this task in Mingle
        alm_task = self.alm_get_task(task)
        if not alm_task:
            raise AlmException('Alm task not added successfully for %s. Please '
                               'check ALM-specific settings in config file' % task['id'])

        if self.config['alm_standard_workflow'] and (task['status'] == 'DONE' or task['status'] == 'NA'):
            self.alm_update_task_status(alm_task, task['status'])

        return 'Project: %s, Card: %s' % (self.sde_plugin.config['alm_project'],
                                          alm_task.get_alm_id())

    def alm_update_task_status(self, task, status):
        if not task:
            logger.debug('Status synchronization disabled')
            return

        status_args = {'card[properties][][name]': 'status'}

        if status == 'DONE' or status == 'NA':
            status_args['card[properties][][value]'] = self.sde_plugin.config['mingle_done_statuses'][0]
        elif status == 'TODO':
            status_args['card[properties][][value]'] = self.sde_plugin.config['mingle_new_status']
        else:
            raise AlmException('Invalid status %s' % status)

        try:
            self.alm_plugin.call_api('%s/cards/%s.xml' % (self.project_uri, task.get_alm_id()),
                                     args=status_args, method=URLRequest.PUT)
        except APIError, err:
            raise AlmException('Unable to update task status to %s for card: %s in Mingle because of %s' %
                               (status, task.get_alm_id(), err))

        logger.debug('Status changed to %s for task %s in Mingle' % (status, task.get_alm_id()))

    def alm_disconnect(self):
        pass

    def convert_markdown_to_alm(self, content, ref): 
        return self.mark_down_converter.convert(content)
