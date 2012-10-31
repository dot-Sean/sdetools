from sdelib.cmd import BaseCommand
from sdelib.interactive_plugin import PlugInExperience
from modules.mingle.lib.mingle_plugin import MingleConnector, MingleAPIBase
from modules.mingle.lib.mingle_plugin import add_mingle_config_options
from alm_integration.alm_plugin_base import AlmException
from sdelib.interactive_plugin import PluginError


class Command(BaseCommand):
    help = 'Mingle <-> SDE sync utility.'

    def configure(self):
        add_mingle_config_options(self.config)

    def handle(self):
        try:
            sde_plugin = PlugInExperience(self.config)
            mbase = MingleAPIBase(self.config)
            mingle = JIRAConnector(sde_plugin, mbase)
            mingle.synchronize()
        except (AlmException, PluginError), err:
            print 'The following error was encountered: %s' % err
            return False
        return True
