import re
import urllib

from urlparse import parse_qsl
from sdetools.sdelib.testlib.response_generator import ResponseGenerator
from sdetools.sdelib.commons import urlencode_str


class MingleResponseGenerator(ResponseGenerator):
    def __init__(self, config, test_dir=None):
        resource_templates = ['card.xml']
        self.project_uri = '/org_name/api/v2/projects/%s' % urlencode_str(urlencode_str(config['alm_project']))
        rest_api_targets = {
            '/org_name/api/v2/projects.xml': 'get_projects',
            '%s.xml' % self.project_uri: 'get_project',
            '%s/cards.xml' % self.project_uri: 'call_cards',
            '%s/cards/[0-9]+.xml' % self.project_uri: 'call_card_by_number',
            '%s/card_types.xml' % self.project_uri: 'get_card_types',
            '%s/property_definitions.xml' % self.project_uri: 'get_property_definitions',
            '%s/property_definitions/[0-9]+.xml' % self.project_uri: 'get_property_definition_by_id'
        }
        super(MingleResponseGenerator, self).__init__(rest_api_targets, resource_templates, test_dir)

    @staticmethod
    def encode_response(response):
        if response:
            return response.toxml()
        else:
            return ''

    @staticmethod
    def decode_data(data):
        try:
            qs = urllib.unquote_plus(data).decode('utf-8')

            return dict(parse_qsl(qs))
        except:
            return data

    """
       Response functions 
    """
    def get_property_definition_by_id(self, target, flag, data, method):
        property_id = re.search('[0-9]+(?=\.xml)', target).group(0)

        if not flag:
            if property_id == '114':
                return self.get_xml_from_file('status_definition')
            else:
                self.raise_error('404')
        else:
            self.raise_error('401')

    def get_property_definitions(self, target, flag, data, method):
        if not flag:
            return self.get_xml_from_file('property_definitions')
        else:
            self.raise_error('401')

    def get_card_types(self, target, flag, data, method):
        if not flag:
            return self.get_xml_from_file('card_types')
        else:
            self.raise_error('401')

    def get_project(self, target, flag, data, method):
        if not flag:
            return self.get_xml_from_file('project')
        elif flag == 'anonymous_accessible':
            xml = self.get_xml_from_file('project')
            element = xml.getElementsByTagName('anonymous_accessible')[0]
            element.firstChild.nodeValue = 'true'

            return xml
        else:
            self.raise_error('401')

    def get_projects(self, target, flag, data, method):
        if not flag:
            return self.get_xml_from_file('projects')
        elif flag == 'anonymous_accessible':
            xml = self.get_xml_from_file('projects')
            element = xml.getElementsByTagName('anonymous_accessible')[0]
            element.firstChild.nodeValue = 'true'

            return xml
        else:
            self.raise_error('401')

    def call_cards(self, target, flag, data, method):
        if not flag:
            if method == 'GET':
                cards = self.get_xml_from_file('cards')

                if data:
                    _mingle_tasks = []
                    filter_arg = data.get('filters[]')
                    card_name = re.search('(?<=\[Name\]\[is\]\[).*(?=\])', filter_arg).group(0)
                    card_number = self.extract_task_number_from_title(card_name)
                    task = self.generator_get_resource('card', card_number)

                    if task:
                        _mingle_tasks.append(task)
                else:
                    _mingle_tasks = self.generator_get_all_resource('card')

                for task in _mingle_tasks:
                    cards.documentElement.appendChild(task.documentElement)

                return cards
            elif method == 'POST':
                resource_data = {
                    'id': self.extract_task_number_from_title(data['card[name]']),
                    'title': data['card[name]'],
                    'card_type': data['card[card_type_name]'],
                    'description': data['card[description]'],
                    'status': data['card[properties][][value]']
                }
                self.generator_add_resource('card', resource_data['id'], resource_data)
                return None
        else:
            self.raise_error('401')

    def call_card_by_number(self, target, flag, data, method):
        if not flag:
            card_number = re.search('[0-9]+(?=\.xml)', target).group(0)

            if method == 'GET':
                return self.generator_get_resource('card', card_number)
            elif method == 'PUT':
                status = data['card[properties][][value]']

                if self.generator_get_resource('card', card_number):
                    self.generator_update_resource('card', card_number, {'status': status})

            return None
        else:
            self.raise_error('401')

    """

       XML Generator
    """
    def generate_resource_from_template(self, resource_type, resource_data):
        self._check_resource_type_exists(resource_type)

        card = self.get_xml_from_file('card')
        name_node = card.getElementsByTagName('name').item(0)
        name_node.firstChild.nodeValue = resource_data['title']

        number_node = card.getElementsByTagName('number').item(0)
        number_node.firstChild.nodeValue = int(resource_data['id'])

        description_node = card.getElementsByTagName('description').item(0)
        description_node.firstChild.nodeValue = resource_data['description']

        id_node = card.getElementsByTagName('id').item(0)
        id_node.firstChild.nodeValue = int(resource_data['id'])

        properties = card.getElementsByTagName('property')
        for prop in properties:
            if (prop.getElementsByTagName('name').item(0).firstChild.nodeValue == 'Status'):
                status_node = prop.getElementsByTagName('value').item(0).firstChild
                status_node.nodeValue = resource_data['status']

        card_type_node = card.getElementsByTagName('card_type').item(0)
        card_type_name_node = card_type_node.getElementsByTagName('name').item(0)
        card_type_name_node.firstChild.nodeValue = resource_data['card_type']

        return card
