# Copyright SDElements Inc
#
# Plugin for two way integration with JIRA

from sdetools.sdelib.cmd import BaseCommand
from sdetools.modules.sync_jira.jira_rest import JIRARestAPI
from sdetools.modules.sync_jira.jira_soap import JIRASoapAPI
from sdetools.modules.sync_jira.jira_plugin import JIRAConnector
from sdetools.alm_integration.alm_plugin_base import AlmException
from sdetools.sdelib.interactive_plugin import PluginError

class Command(BaseCommand):
    help = 'JIRA <-> SDE sync utility.'
    sub_cmds = ['4', '5', '6']

    def configure(self):
        self.config.add_custom_option('jira_version', 'Version of JIRA [e.g. 4.3.3, 5, or 6.0]', 
                default='6')

        # We start with REST to get configuration and other stuff right
        # Then we switch to SOAP for JIRA 4 if we need to
        alm_api = JIRARestAPI(self.config)
        self.jira = JIRAConnector(self.config, alm_api)

    def handle(self):
        api_ver = self.config['jira_version'][:1]
        if api_ver not in ['4', '5', '6']:
            raise AlmException('Only JIRA versions 4.3.3 and up are supported')
        self.config.jira_api_ver = int(api_ver)

        if self.config.jira_api_ver == 4:
            self.jira.alm_plugin = JIRASoapAPI(self.config)
            
        self.jira.initialize()
        self.jira.synchronize()

        return True
