import re
import os

from sdetools.sdelib.testlib.alm_response_generator import ResponseGenerator
from sdetools.sdelib.commons import urlencode_str


class MingleResponseGenerator(ResponseGenerator):
    BASE_PATH = 'api/v2'
    STATUS_NAMES = ['New', 'Done']

    def __init__(self, project_name):
        initial_task_status = self.STATUS_NAMES[0]
        test_dir = os.path.dirname(os.path.abspath(__file__)) 
        super(MingleResponseGenerator, self).__init__(initial_task_status, test_dir)

        self.project_uri = 'projects/%s/cards' % urlencode_str(project_name)
        self.rest_api_targets = {
            'projects.xml': 'get_projects',
            '%s.xml' % self.project_uri: 'project_cards',
            '%s/[0-9]*.xml' % self.project_uri: 'update_card_status'
        }

    """
       Response functions 
    """
    def get_projects(self, target, flag, data, method):
        if not flag:
            return self.get_xml_from_file('projects')
        else:
            self.raise_error('401')

    def project_cards(self, target, flag, data, method):
        if not flag:
            if method == 'GET':
                cards = self.get_xml_from_file('cards')

                if data:
                    filter_arg = data.get('filters[]')
                    card_name = re.search('(?<=\[Name\]\[is\]\[).*(?=\])', filter_arg).group(0)
                    card_number = self.extract_task_number_from_title(card_name)
                    task = self.generator_get_task(card_number)

                    if task:
                        card = self.generate_card(card_number, task['name'], task['status'], task['card_type'])
                        cards.documentElement.appendChild(card.documentElement)

                return cards
            elif method == 'POST':
                card_name = data['card[name]']
                card_type = data['card[card_type_name]']
                status = data['card[properties][][value]']
                card_number = self.extract_task_number_from_title(card_name)
                self.generator_add_task(card_number, card_name, status)
                self.generator_update_task(card_number, 'card_type', card_type)

                return None
        else:
            self.raise_error('401')

    def update_card_status(self, target, flag, data, method):
        if not flag:
            status = data['card[properties][][value]']
            card_number = re.search('[0-9]+(?=\.xml)', target).group(0)

            if self.generator_get_task(card_number):
                self.generator_update_task(card_number, 'status', status)

            return None
        else:
            self.raise_error('401')

    """

       XML Generator
    """
    def generate_card(self, card_id, card_name, status, card_type):
        card = self.get_xml_from_file('card')
        name_node = card.getElementsByTagName('name').item(0)
        name_node.firstChild.nodeValue = card_name

        number_node = card.getElementsByTagName('number').item(0)
        number_node.firstChild.nodeValue = int(card_id)

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
