# Copyright SDElements Inc
#
# Plugin for two way integration with Mingle

import sys, os
sys.path.append(os.path.split(os.path.split(os.path.abspath(__file__))[0])[0])

from sdelib.conf_mgr import config
from sdelib.interactive_plugin import PlugInExperience

from mingle_integration.lib.mingle_plugin import MingleConnector
from mingle_integration.lib.mingle_plugin import add_mingle_config_options
from mingle_integration.lib.mingle_apiclient import MingleAPIBase
from alm_integration.alm_plugin_base import AlmException
from sdelib.interactive_plugin import PluginError

def main(argv):
    try:
        add_mingle_config_options(config)
        ret = config.parse_args(argv)
        if not ret:
            sys.exit(1)
        sde_plugin = PlugInExperience(config)
        mbase = MingleAPIBase(config)
        mingle = MingleConnector(sde_plugin, mbase)
        mingle.synchronize()
    except (AlmException, PluginError), err:
        print 'The following error was encountered: %s' % err

if __name__ == "__main__":
    main(sys.argv)
