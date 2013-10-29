import re

from sdetools.sdelib.testlib.response_generator import ResponseGenerator
from sdetools.sdelib.commons import urlencode_str


class MingleResponseGenerator(ResponseGenerator):
    BASE_PATH = 'api/v2'

    def __init__(self, config, test_dir=None):
        project_name = urlencode_str(config['alm_project'])
        statuses = ['New', 'Closed', 'Open']
        self.project_uri = 'projects/%s' % urlencode_str(project_name)
        rest_api_targets = {
            'projects.xml': 'get_projects',
            '%s.xml' % self.project_uri: 'get_project',
            '%s/cards.xml' % self.project_uri: 'call_cards',
            '%s/cards/[0-9]+.xml' % self.project_uri: 'call_card_by_number',
            '%s/card_types.xml' % self.project_uri: 'get_card_types',
            '%s/property_definitions.xml' % self.project_uri: 'get_property_definitions',
            '%s/property_definitions/[0-9]+.xml' % self.project_uri: 'get_property_definition_by_id'
        }
        super(MingleResponseGenerator, self).__init__(rest_api_targets, statuses, test_dir)

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
                _mingle_tasks = self.generator_get_all_tasks().values()

                if data:
                    _mingle_tasks = []
                    filter_arg = data.get('filters[]')
                    card_name = re.search('(?<=\[Name\]\[is\]\[).*(?=\])', filter_arg).group(0)
                    card_number = self.extract_task_number_from_title(card_name)
                    task = self.generator_get_task(card_number)

                    if task:
                        _mingle_tasks.append(task)

                for task in _mingle_tasks:
                    card = self.generate_card(task['id'], task['name'], task['status'], task['card_type'], task['description'])
                    cards.documentElement.appendChild(card.documentElement)

                return cards
            elif method == 'POST':
                card_name = data['card[name]']
                card_type = data['card[card_type_name]']
                description = data['card[description]']
                status = data['card[properties][][value]']
                card_number = self.extract_task_number_from_title(card_name)
                self.generator_add_task(card_number, card_name, status)
                self.generator_update_task(card_number, 'card_type', card_type)
                self.generator_update_task(card_number, 'description', description)
                return None
        else:
            self.raise_error('401')

    def call_card_by_number(self, target, flag, data, method):
        if not flag:
            card_number = re.search('[0-9]+(?=\.xml)', target).group(0)

            if method == 'GET':
                task = self.generator_get_task(card_number)

                if task:
                    return self.generate_card(card_number, task['name'], task['status'], task['card_type'], task['description'])
            elif method == 'PUT':
                status = data['card[properties][][value]']

                if self.generator_get_task(card_number):
                    self.generator_update_task(card_number, 'status', status)

            return None
        else:
            self.raise_error('401')

    """

       XML Generator
    """
    def generate_card(self, card_id, card_name, status, card_type, description):
        card = self.get_xml_from_file('card')
        name_node = card.getElementsByTagName('name').item(0)
        name_node.firstChild.nodeValue = card_name

        number_node = card.getElementsByTagName('number').item(0)
        number_node.firstChild.nodeValue = int(card_id)

        description_node = card.getElementsByTagName('description').item(0)
        description_node.firstChild.nodeValue = description

        id_node = card.getElementsByTagName('id').item(0)
        id_node.firstChild.nodeValue = int(card_id)

        properties = card.getElementsByTagName('property')
        for prop in properties:
            if (prop.getElementsByTagName('name').item(0).firstChild.nodeValue == 'Status'):
                status_node = prop.getElementsByTagName('value').item(0).firstChild
                status_node.nodeValue = status

        card_type_node = card.getElementsByTagName('card_type').item(0)
        card_type_name_node = card_type_node.getElementsByTagName('name').item(0)
        card_type_name_node.firstChild.nodeValue = card_type

        return card
