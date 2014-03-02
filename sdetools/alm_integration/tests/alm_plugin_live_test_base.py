import os

from sdetools.sdelib.mod_mgr import ReturnChannel, load_modules
from sdetools.sdelib.conf_mgr import Config
from sdetools.sdelib.commons import abc, Error, get_directory_of_current_module
from sdetools.alm_integration.alm_plugin_base import AlmException
from testconfig import config

abstractmethod = abc.abstractmethod
CONF_FILE_LOCATION = 'test_settings.conf'

def stdout_callback(obj):
    print obj


class AlmPluginLiveTestBase(object):
    @classmethod
    def setUpClass(cls, connector, api):

        if 'sdetools' not in config:
            raise Exception("Missing configuration for sdetools config_path")

        cls.connector_cls = connector
        cls.api_cls = api
        cls.conf_path = config['sdetools']['config_path']
        cls.ret_chn = ReturnChannel(stdout_callback, {})

    def setUp(self):
        command_list = load_modules()
        self.config = Config('help', '', command_list, [], self.ret_chn, 'shell')
        self.init_alm_connector()
        self.pre_parse_config()
        self.config.import_custom_options()
        Config.parse_config_file(self.config, self.conf_path)
        self.post_parse_config()

    def tearDown(self):
        pass

    def pre_parse_config(self):
        pass

    def post_parse_config(self):
        pass

    def init_alm_connector(self):
        if self.connector_cls is None:
            raise Error('No alm connector found')
        elif self.api_cls is None:
            raise Error('No alm api found')
        else:
            self.connector = self.connector_cls(self.config, self.api_cls(self.config))

    def test_bad_user(self):
        self.config['alm_user'] = 'XXXXX'
        self.connector.config = self.config
        self.connector.initialize()
        try:
            self.connector.alm_connect()
        except AlmException:
            pass

    def test_bad_server(self):
        self.config['alm_server'] = 'XXXXX'
        self.connector.config = self.config
        self.connector.initialize()
        try:
            self.connector.alm_connect()
        except AlmException:
            pass

    def test_alm_connect_server(self):
        self.config['test_alm'] = 'server'
        self.connector.config = self.config
        self.connector.initialize()
        self.connector.alm_connect()

    def test_alm_connect_project(self):
        self.config['test_alm'] = 'project'
        self.connector.config = self.config
        self.connector.initialize()
        self.connector.alm_connect()

    def test_alm_connect_settings(self):
        self.config['test_alm'] = 'settings'
        self.connector.config = self.config
        self.connector.initialize()
        self.connector.alm_connect()

    def synchronize(self, master):
        self.config['test_alm'] = ''
        self.config['conflict_policy'] = master
        self.connector.config = self.config
        self.connector.initialize()

        for i in range(2):
            # synchronize the two systems
            self.connector.synchronize()

            tasks = self.connector.sde_get_tasks()
            pruned_tasks = self.connector.prune_tasks(tasks)

            for task in pruned_tasks:
                alm_task = self.connector.alm_get_task(task)
                self.assertNotNone(alm_task, 'Missing Alm task for %s' % task['id'])
                self.assertTrue(self.connector.status_match(alm_task.get_status(), task['status']))

                # invert the status and get ready to synchronize again
                self.connector.sde_update_task_status(task, self._inverted_status(task['status']))

    def test_synchronize_sde_as_master(self):
        self.synchronize('sde')

    def test_synchronize_alm_as_master(self):
        self.synchronize('alm')

    def _inverted_status(self, status):
        if status == 'DONE':
            return 'TODO'
        else:
            return 'DONE'

    @staticmethod
    def assertNotNone(obj, msg=None):
        if obj is None:
            if not msg:
                msg = 'Expected a value other than None'

            raise AssertionError(msg)