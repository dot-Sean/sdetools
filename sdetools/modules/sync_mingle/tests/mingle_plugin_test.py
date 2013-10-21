import unittest

from mingle_response_generator import MingleResponseGenerator
from sdetools.alm_integration.tests.alm_plugin_test_base import AlmPluginTestBase
from sdetools.modules.sync_mingle.mingle_plugin import MingleConnector, MingleAPIBase
PATH_TO_ALM_REST_API = 'sdetools.modules.sync_mingle.mingle_plugin'


class TestMingleCase(AlmPluginTestBase, unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        alm_classes = [MingleConnector, MingleAPIBase, MingleResponseGenerator]
        super(TestMingleCase, cls).setUpClass(PATH_TO_ALM_REST_API, alm_classes=alm_classes)

    def test_parsing_alm_task(self):
        result = super(TestMingleCase, self).test_parsing_alm_task()
        test_task = result[0]
        test_task_result = result[1]

        alm_id = int(test_task['id'].split('T')[1])
        result_alm_id = test_task_result.get_alm_id()

        self.assertEqual(type(result_alm_id), int, 'Expected alm_id to be an integer')
        self.assertEqual(result_alm_id, alm_id, 'Expected alm_id %s, got %s' % (alm_id, result_alm_id))

    def test_mingle_cached_cards(self):
        self.connector.alm_connect()
        test_task = self.mock_sde_response.generate_sde_task()
        self.connector.alm_add_task(test_task)
        cached_cards = self.connector.cached_cards

        self.assertEqual(cached_cards, None)

        self.connector._cache_all_sde_mingle_cards()
        cached_cards = self.connector.cached_cards
        sde_task_id = self.connector._extract_task_id(test_task['id'])
        alm_id = int(test_task['id'].split('T')[1])

        self.assertNotNone(cached_cards)
        self.assertNotNone(cached_cards.get(sde_task_id))
        self.assertEquals(cached_cards.get(sde_task_id), alm_id)
        self.assertNotNone(self.connector.alm_get_task(test_task))