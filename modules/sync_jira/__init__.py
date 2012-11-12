# Copyright SDElements Inc
#
# Plugin for two way integration with JIRA

from sdelib.cmd import BaseCommand
from modules.sync_jira.jira_rest import JIRARestAPI
from modules.sync_jira.jira_soap import JIRASoapAPI
from modules.sync_jira.jira_plugin import JIRAConnector
from alm_integration.alm_plugin_base import AlmException
from sdelib.interactive_plugin import PluginError

class Command(BaseCommand):
    help = 'JIRA <-> SDE sync utility.'

    def configure(self):
        self.config.add_custom_option('jira_version', 'Version of JIRA [4 or 5]', default='5')

        # We start with REST to get configuration and other stuff right
        # Then we switch to SOAP for JIRA 4 if we need to
        jbase = JIRARestAPI(self.config)
        self.jira = JIRAConnector(self.config, jbase)

    def handle(self):
        api_ver = self.config['jira_version'][:1]
        if api_ver not in ['4', '5']:
            raise AlmException('Only JIRA versions 4.4 and 5 are supported')
        self.config.jira_api_ver = int(api_ver)

        if self.config.jira_api_ver == 4:
            self.jira.alm_plugin = JIRASoapAPI(self.config)
            
        self.jira.initialize()
        self.jira.synchronize()

        return True
