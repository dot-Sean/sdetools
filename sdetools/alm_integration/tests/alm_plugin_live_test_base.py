from sdetools.sdelib.mod_mgr import ReturnChannel, load_modules
from sdetools.sdelib.conf_mgr import Config
from sdetools.sdelib.commons import Error
from sdetools.alm_integration.alm_plugin_base import AlmException
from testconfig import config


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
        self.config.import_custom_options()
        Config.parse_config_file(self.config, self.conf_path)

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

    def test_sde_connect(self):
        self.config['test_alm'] = 'server'
        self.connector.config = self.config
        self.connector.initialize()
        self.connector.sde_connect()
        self.assertTrue(self.connector.is_sde_connected, True)

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

        # Only refresh tasks if the configuration has this option explicitly set
        refresh_tasks = self.connector.config['start_fresh'] and self.connector.alm_supports_delete()

        alm_tasks = {}

        for i in xrange(2):

            # clean out any existing issues on the first run, if possible
            if i == 1 and refresh_tasks:
                self.connector.config['start_fresh'] = True
            else:
                self.connector.config['start_fresh'] = False

            # synchronize the two systems
            self.connector.synchronize()

            tasks = self.connector.sde_get_tasks()
            filtered_tasks = self.connector.filter_tasks(tasks)

            for task in filtered_tasks:
                alm_task = self.connector.alm_get_task(task)
                self.assertNotNone(alm_task, 'Missing Alm task for %s' % task['id'])
                self.assertTrue(self.connector.status_match(alm_task.get_status(), task['status']))

                # invert the status and get ready to synchronize again
                self.connector.sde_update_task_status(task, self._inverted_status(task['status']))

                # Remaining tests are only applicable if connector supports delete
                if not refresh_tasks:
                    continue

                # Make sure we're creating new ALM tasks
                if i == 0:
                    alm_tasks[task['id']] = alm_task.get_alm_id()
                elif i == 1:
                    self.assertNotEqual(alm_tasks[task['id']], alm_task.get_alm_id())

    def test_synchronize_sde_as_master(self):
        self.synchronize('sde')

    def test_synchronize_alm_as_master(self):
        self.synchronize('alm')

    def _inverted_status(self, status):
        return 'DONE' if status == 'TODO' else 'TODO'

    @staticmethod
    def assertNotNone(obj, msg=None):
        if obj is None:
            if not msg:
                msg = 'Expected a value other than None'

            raise AssertionError(msg)