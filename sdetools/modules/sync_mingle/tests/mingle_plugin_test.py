import unittest

from mingle_response_generator import MingleResponseGenerator
from sdetools.alm_integration.tests.alm_plugin_test_base import AlmPluginTestBase
from sdetools.modules.sync_mingle.mingle_plugin import MingleConnector, MingleAPIBase, AlmException


class TestMingleCase(AlmPluginTestBase, unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        alm_classes = [MingleConnector, MingleAPIBase, MingleResponseGenerator]
        super(TestMingleCase, cls).setUpClass(alm_classes=alm_classes)

    def test_parsing_alm_task(self):
        result = super(TestMingleCase, self).test_parsing_alm_task()
        test_task = result[0]
        test_task_result = result[1]

        alm_id = test_task['id'].split('T')[1]
        result_alm_id = test_task_result.get_alm_id()

        self.assertEqual(result_alm_id, alm_id, 'Expected alm_id %s, got %s' % (alm_id, result_alm_id))

    def test_mingle_cached_cards(self):
        self.connector.alm_connect()
        test_task = self.mock_sde_response.generate_sde_task()
        sde_task_id = self.connector._extract_task_id(test_task['id'])
        alm_id = test_task['id'].split('T')[1]

        self.connector.alm_add_task(test_task)
        cached_cards = self.connector.cached_cards

        self.assertEqual(cached_cards, {sde_task_id: alm_id})

        self.connector._cache_all_sde_mingle_cards()
        cached_cards = self.connector.cached_cards

        self.assertNotNone(cached_cards)
        self.assertNotNone(cached_cards.get(sde_task_id))
        self.assertEquals(cached_cards.get(sde_task_id), alm_id)
        self.assertNotNone(self.connector.alm_get_task(test_task))

    def test_invalid_config_card_type(self):
        self.connector.config['mingle_card_type'] = 'INVALID-CARD-TYPE'
        exception_msg = ("The given mingle card type 'INVALID-CARD-TYPE' is not one of the valid card types: "
                         "Story, Bug")

        self.assert_exception(AlmException, '', exception_msg, self.connector.alm_connect)

    def test_invalid_config_new_status(self):
        self.connector.config['mingle_new_status'] = 'BAD_NEW_STATUS'
        exception_msg = ("Invalid mingle_new_status BAD_NEW_STATUS. Expected one of"
                         " New, Open, Closed")

        self.assert_exception(AlmException, '', exception_msg, self.connector.alm_connect)

    def test_invalid_config_done_statuses(self):
        self.connector.config['mingle_done_statuses'] = ['BAD_DONE_STATUS_1', 'New']
        exception_msg = ("Invalid mingle_done_statuses: BAD_DONE_STATUS_1. Expected one of"
                         " New, Open, Closed")

        self.assert_exception(AlmException, '', exception_msg, self.connector.alm_connect)

    def test_content_on_public_repo(self):
        PUBLIC_TASK_CONTENT = ("Visit us at http://www.sdelements.com/ to find out how you can easily add project-"
                               "specific software security requirements to your existing development processes.")

        self.mock_alm_response.set_response_flags({'get_project': 'anonymous_accessible'})
        self.connector.alm_connect()
        test_task = self.mock_sde_response.generate_sde_task()
        self.connector.alm_add_task(test_task)
        alm_id = int(test_task['id'].split('T')[1])
        headers, card = self.connector.alm_plugin.call_api('%s/cards/%s.xml' % (self.connector.project_uri, alm_id))

        self.assertNotNone(card.getElementsByTagName('description'), 'Failed to find the description field')
        description = self.connector._get_value_of_element_with_tag(card, 'description')
        self.assertEqual(description, PUBLIC_TASK_CONTENT, 'Expected description to be %s, got %s' %
                                                           (PUBLIC_TASK_CONTENT, description))

    def test_alm_priority_map(self):
        # Custom priority maps are unsupported in this integration
        pass