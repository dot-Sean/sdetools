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


