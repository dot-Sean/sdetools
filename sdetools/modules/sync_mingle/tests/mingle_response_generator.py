import re
import os
import sys

from urllib2 import HTTPError
from mock import MagicMock

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))))
from sdetools.alm_integration.tests.alm_response_generator import AlmResponseGenerator
from sdetools.sdelib.commons import urlencode_str

class MingleResponseGenerator(AlmResponseGenerator):
    BASE_PATH = 'api/v2'
    STATUS_NAMES = ['New', 'Done']
    REST_API_TARGETS = {
        'get_projects': 'projects.xml',
        'project_cards': '%s.xml',
        'update_card_status': '%s/[0-9]*.xml'
    }

    def __init__(self, project_name):
        initial_task_status = self.STATUS_NAMES[0]
        test_dir = os.path.dirname(os.path.abspath(__file__)) 
        super(MingleResponseGenerator, self).__init__(initial_task_status, test_dir)
        self.project_uri = 'projects/%s/cards' % urlencode_str(project_name)

    def get_response(self, target, flag, data, method):
        if target == self.REST_API_TARGETS['get_projects']:
            return self.get_projects(flag.get('get_projects'))
        elif target == self.REST_API_TARGETS['project_cards'] % self.project_uri:
            return self.project_cards(flag.get('project_cards'), data, method)
        elif re.match(self.REST_API_TARGETS['update_card_status'] % self.project_uri, target):
            return self.update_card_status(flag.get('update_card_status'), target, data)
        else:
            self.raise_error('404')

    def raise_error(self, error_code, return_value=None):
        fp_mock = MagicMock()

        if error_code == '400':
            message = 'Invalid parameters'
        elif error_code == '403':
            message = 'No permission'
        elif error_code == '404':
            message = 'Not found'
        elif error_code == '500':
            message = 'Server error'
        else:
            message = 'Unknown error'

        if not return_value:
            fp_mock.read.return_value = message
        else:
            fp_mock.read.return_value = return_value

        raise HTTPError('', error_code, message, '', fp_mock)

    """
       Response functions 
    """
    def get_projects(self, flag):
        if not flag:
            return self.get_xml_from_file('projects')
        else:
            self.raise_error('401')

    def project_cards(self, flag, data, method):
        if not flag:
            if method == 'GET':
                cards = self.get_xml_from_file('cards')

                if data:
                    filter_arg = data.get('filters[]')
                    card_name = re.search('(?<=\[Name\]\[is\]\[).*(?=\])', filter_arg).group(0)
                    card_number = self.get_task_number_from_title(card_name)
                    task = self.get_alm_task(card_number)

                    if task:
                        card = self.generate_card(card_number, task['name'], task['status'], task['card_type'])
                        cards.documentElement.appendChild(card.documentElement)

                return cards
            elif method == 'POST':
                card_name = data['card[name]']
                card_type = data['card[card_type_name]']
                status = data['card[properties][][value]']
                card_number = self.get_task_number_from_title(card_name)
                self.add_alm_task(card_number, card_name, status)
                self.update_alm_task(card_number, 'card_type', card_type)

                return None
        else:
            self.raise_error('401')

    def update_card_status(self, flag, target, data):
        if not flag:
            status = data['card[properties][][value]']
            card_number = re.search('[0-9]+(?=\.xml)', target).group(0)

            if self.get_alm_task(card_number):
                self.update_alm_task(card_number, 'status', status)

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

