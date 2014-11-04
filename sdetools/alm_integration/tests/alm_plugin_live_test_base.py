from sdetools.sdelib.mod_mgr import ReturnChannel, load_modules
from sdetools.sdelib.conf_mgr import Config
from sdetools.sdelib.commons import Error
from sdetools.alm_integration.alm_plugin_base import AlmConnector, AlmException
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

    def test_alm_task_delete(self):
        if not self.connector.alm_supports_delete():
            return

        self.config['test_alm'] = ''
        self.connector.config = self.config
        self.connector.config['start_fresh'] = True
        self.connector.initialize()
        self.connector.sde_connect()
        self.connector.alm_connect()
        tasks = self.connector.sde_get_tasks()
        filtered_tasks = self.connector.filter_tasks(tasks)

        if not filtered_tasks:
            return

        test_task = filtered_tasks[0]
        self.connector.alm_add_task(test_task)
        alm_task1 = self.connector.alm_get_task(test_task)
        self.assertNotNone(alm_task1, 'Missing Alm task for %s' % test_task['id'])
        self.connector.alm_remove_task(alm_task1)
        alm_task2 = self.connector.alm_get_task(test_task)
        if alm_task2:
            self.assertNotEqual(alm_task1.get_alm_id(), alm_task2.get_alm_id(),
                                'Could not delete task %s in alm' % test_task['id'])

    def synchronize(self, options):
        options['test_alm'] = ''

        self._update_config(options)
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

                if self.config['alm_standard_workflow']:
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
        self.synchronize({'conflict_policy': 'sde'})

    def test_synchronize_alm_as_master(self):
        self.synchronize({'conflict_policy': 'alm'})

    def _update_config(self, options):
        for key in options:
            self.config[key] = options[key]
        self.connector.config = self.config

    def test_synchronize_similar_tasks(self):
        self.connector.initialize()
        self.connector.sde_connect()
        self.connector.alm_connect()

        tasks = self.connector.sde_get_tasks()
        filtered_tasks = self.connector.filter_tasks(tasks)
        self.assertTrue(len(filtered_tasks) > 0)
        task = filtered_tasks[0]
        test_task = task.copy()

        task_id = test_task['id']
        title = test_task['title']

        # construct a similar task (T21 => T21222222) and add to the ALM
        task['id'] = '%s222222' % test_task['id']
        task['title'] = '%s: Sample Title' % AlmConnector._extract_task_id(task['id'])
        task = AlmConnector.add_alm_title(self.connector.config, task)

        # re-use an issue if one already exists in the ALM
        alm_task1 = self.connector.alm_get_task(task)
        if not alm_task1:
            ref = self.connector.alm_add_task(task)
            self.assertNotNone(ref)
            alm_task1 = self.connector.alm_get_task(task)

        # Try to sync a similar task
        test_task['id'] = task_id
        test_task['title'] = title
        test_task = AlmConnector.add_alm_title(self.connector.config, test_task)
        alm_task2 = self.connector.alm_get_task(test_task)
        if not alm_task2:
            ref = self.connector.alm_add_task(test_task)
            self.assertNotNone(ref)
            alm_task2 = self.connector.alm_get_task(test_task)

        self.assertNotEqual(alm_task1.get_alm_id(), alm_task2.get_alm_id())

        # clean-up issues in the ALM
        if not self.connector.alm_supports_delete():
            return

        if alm_task1:
            self.connector.alm_remove_task(alm_task1)

        if alm_task2:
            self.connector.alm_remove_task(alm_task2)

    def test_custom_titles(self):

        scenario_options = {
            'alm_standard_workflow': False,
            'alm_context': 'Context',
        }

        scenario1_alm_title_format = '[$application-$project] $task_id $title'
        scenario2_alm_title_format = '[$context] $task_id $title'

        self._update_config(scenario_options)
        self.connector.initialize()

        tasks = self.connector.sde_get_tasks()
        filtered_tasks = self.connector.filter_tasks(tasks)

        scenario_options['alm_title_format'] = scenario1_alm_title_format
        self.synchronize(scenario_options)

        scenario_options['alm_title_format'] = scenario2_alm_title_format
        self.synchronize(scenario_options)

        for task in filtered_tasks:
            # Find the corresponding scenario1 alm task
            scenario_options['alm_title_format'] = scenario1_alm_title_format
            self._update_config(scenario_options)
            scenario1_task = AlmConnector.add_alm_title(self.connector.config, task.copy())
            scenario1_alm_task = self.connector.alm_get_task(scenario1_task)

            # Find the corresponding scenario2 alm task
            scenario_options['alm_title_format'] = scenario2_alm_title_format
            self._update_config(scenario_options)
            scenario2_task = AlmConnector.add_alm_title(self.connector.config, task.copy())
            scenario2_alm_task = self.connector.alm_get_task(scenario2_task)

            # Check that these alm tasks are distinct for the same sde task
            self.assertNotEqual(scenario1_alm_task.get_alm_id(), scenario2_alm_task.get_alm_id())

            # Update the first alm task to the opposite of the second alm task's status
            scenario2_status = scenario2_alm_task.get_status()
            self.connector.alm_update_task_status(scenario1_alm_task, self._inverted_status(scenario2_status))

            scenario1_alm_task = self.connector.alm_get_task(scenario1_task)
            scenario2_alm_task = self.connector.alm_get_task(scenario2_task)

            # Make sure the first alm task status updated and the second one remained the same
            self.assertTrue(self.connector.status_match(scenario1_alm_task.get_status(),
                                                        self._inverted_status(scenario2_status)))
            self.assertTrue(self.connector.status_match(scenario2_alm_task.get_status(), scenario2_status))

            # Update the second alm task to the opposite of the first alm task's status
            scenario1_status = scenario1_alm_task.get_status()
            self.connector.alm_update_task_status(scenario2_alm_task, self._inverted_status(scenario1_status))
            scenario2_alm_task = self.connector.alm_get_task(scenario2_task)
            scenario1_alm_task = self.connector.alm_get_task(scenario1_task)

            # Make sure the second alm task status updated and the first one remained the same
            self.assertTrue(self.connector.status_match(scenario2_alm_task.get_status(),
                                                        self._inverted_status(scenario1_status)))
            self.assertTrue(self.connector.status_match(scenario1_alm_task.get_status(), scenario1_status))

    def _inverted_status(self, status):
        return 'DONE' if status == 'TODO' else 'TODO'

    @staticmethod
    def assertNotNone(obj, msg=None):
        if obj is None:
            if not msg:
                msg = 'Expected a value other than None'

            raise AssertionError(msg)