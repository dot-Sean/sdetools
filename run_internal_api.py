#!/usr/bin/python

import sdetools
import sde_int_api

sdetools.set_api_connector(sde_int_api.InternalAPI)

sdetools.call('api_proxy', {'api_func': 'get_applications'})
