import os

from sdetools.sdelib.commons import media_path, UsageError
from sdetools.analysis_integration.base_integrator import BaseIntegrator, IntegrationError
from sdetools.sdelib.restclient import RESTBase, URLRequest, APIError

from sdetools.sdelib import log_mgr
logger = log_mgr.mods.add_mod(__name__)

__all__ = ['WhiteHatIntegrator']

ASSET_TYPE_SITE = 'site'
ASSET_TYPE_APP = 'application'
ASSET_TYPES = [ASSET_TYPE_SITE, ASSET_TYPE_APP]

DEFAULT_MAPPING_FILE = os.path.join(media_path, 'whitehat', 'sde_whitehat_map.xml')


class WhiteHatAPI(RESTBase):
    """ Base plugin for GitHub """

    def __init__(self, config):
        extra_conf_opts = [('wh_api_token', 'WhiteHat API Token', '')]
        super(WhiteHatAPI, self).__init__('wh', 'WhiteHat', config, extra_conf_opts=extra_conf_opts)

    def call_api(self, target, method=URLRequest.GET, args={}, call_headers={}, auth_mode=None):

        args['key'] = self.config['wh_api_token']
        args['accept_fmt'] = 'application/json'
        print args
        try:
            return super(WhiteHatAPI, self).call_api(target, method, args, call_headers, auth_mode)
        except Exception as e:
            raise APIError('API Call failed. Target: %s ; Error: %s' % (target, e))


class WhiteHatIntegrationError(IntegrationError):
    pass


class WhiteHatIntegrator(BaseIntegrator):
    TOOL_NAME = "appscan"

    def __init__(self, wh_api, config):
        self.wh_api = wh_api

        config.opts.add("asset_type", "Asset type: Site or Application (Not required if ID is specified)", None, default='')
        config.opts.add("asset_name", "Asset label (Note required if ID is specified)", None, default='')
        config.opts.add("asset_id", "Asset ID", None, default='')
        config.opts.add("api_key", "API Key", None, default='')

        super(WhiteHatIntegrator, self).__init__(config, self.TOOL_NAME, [], DEFAULT_MAPPING_FILE)

    def initialize(self):
        """
        Post init initialization (must be called first)
        """
        if self.config['asset_type'] not in ASSET_TYPES:
            raise UsageError('Invalid asset type: %s' % self.config['asset_type'])
        super(WhiteHatIntegrator, self).initialize()

    def get_asset_data(self, subresources=[]):
        """
        Retrieves complete asset information by ID
        If ID not given, performs a search by name
        """
        asset_type = self.config['asset_type'].lower()
        asset_id = None

        if not self.config['asset_id']:

            data = self.wh_api.call_api('api/%s' % asset_type)

            if asset_type == ASSET_TYPE_SITE:
                for site in data['sites']:
                    if site['label'] == self.config['asset_name']:
                        asset_id = site['id']
                        break
                else:
                    raise UsageError('Site %s not found. Please check configuration' % self.config['asset_name'])
            else:
                for app in data['collection']:
                    if app['label'] == self.config['asset_name']:
                        asset_id = app['id']
                        break
                else:
                    raise UsageError('Application %s not found. Please check configuration' % self.config['asset_name'])
        else:
            asset_id = self.config['asset_id']

        return self.wh_api.call_api('api/%s/%s' % (asset_type, asset_id) + '/'.join(subresources))

    def get_vuln_data(self, status='open'):
        """
        Retrieves vulnerabilities for a given asset
        By default retrieves only Open vulnerabilities
        """
        asset_id = None
        if not self.config['asset_id']:
            logger.info('Asset ID not specified, retrieving ID by name: %s' % self.config['asset_name'])
            asset_data = self.get_asset_data()
            asset_id = asset_data['id']
        else:
            asset_id = self.config['asset_id']

        logger.info('Retrieving open vulnerabilities')
        data = self.wh_api.call_api('api/vuln', args={'query_site': asset_id, 'query_status': status})

        return data['collection']

    def parse(self):
        logger.info('Fetching vulnerability information')
        data = self.get_vuln_data()
        logger.info('Parsing vulnerability information')
        self.findings = data
        self.report_id = '%s: %s' % (self.config['asset_type'].capitalize(), self.config['asset_name'])

    def _make_finding(self, item):
        return {'weakness_id': item['class'], 'count': 1}

    def generate_findings(self):
        return [self._make_finding(item) for item in self.findings]
