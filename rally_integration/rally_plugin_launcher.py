# Copyright SDElements Inc
#
# Plugin for two way integration with Rally

import sys, os
sys.path.append(os.path.split(os.path.split(os.path.abspath(__file__))[0])[0])

from sdelib.conf_mgr import config
from sdelib.interactive_plugin import PlugInExperience
from sdelib.apiclient import APIBase

from rally_integration.lib.rally_plugin import RallyTask, RallyConnector
from rally_integration.lib.rally_plugin import add_rally_config_options
from rally_integration.lib.rally_plugin import RallyAPIBase
from alm_integration.alm_plugin_base import AlmException
from sdelib.interactive_plugin import PluginError

import logging

def main(argv):
    try:
        add_rally_config_options(config)
        ret = config.parse_args(argv)
        if not ret:
            sys.exit(1)
        sde_plugin = PlugInExperience(config)
        rbase = RallyAPIBase(config)
        rally = RallyConnector(sde_plugin, rbase)
        rally.alm_connect()
        rally.synchronize()
    except (AlmException, PluginError) as e:
        print 'The following error was encountered: %s' % e
 
    
if __name__ == "__main__":
    main(sys.argv)
