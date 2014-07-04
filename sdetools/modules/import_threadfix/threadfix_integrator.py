import os
import urllib

from sdetools.sdelib.commons import media_path, UsageError
from sdetools.analysis_integration.base_integrator import BaseIntegrator, IntegrationError
from sdetools.sdelib.restclient import RESTBase, URLRequest, APIError

from sdetools.sdelib import log_mgr
logger = log_mgr.mods.add_mod(__name__)

__all__ = ['ThreadFixIntegrator']


DEFAULT_MAPPING_FILE = os.path.join(media_path, 'threadfix', 'sde_threadfix_map.xml')


class ThreadFixFormsAPI(RESTBase):

    def __init__(self, config):
        super(ThreadFixFormsAPI, self).__init__('tf', 'ThreadFix', config, setup_config=False)

    def encode_post_args(self, args):
        return urllib.urlencode(args)

    def call_api(self, target, method=URLRequest.POST, args=None, call_headers={}, auth_mode='custom'):

        args['apiKey'] = self.config['tf_api_key']
        call_headers['Accept'] = 'application/json'

        if method == URLRequest.POST:
            call_headers['Content-Type'] = 'application/x-www-form-urlencoded'

        if self.config['tf_context_root']:
            target = "%s/%s" % (self.config['tf_context_root'], target)

        try:
            result = super(ThreadFixFormsAPI, self).call_api(target, method, args, call_headers, auth_mode)
        except Exception as e:
            raise APIError('API Call failed. Target: %s ; Error: %s' % (target, e))

        return result


class ThreadFixAPI(RESTBase):

    def __init__(self, config):
        extra_conf_opts = [
            ('tf_api_key', 'ThreadFix API Token', ''),
            ('tf_context_root', 'ThreadFix Context Root', ''),
        ]
        super(ThreadFixAPI, self).__init__('tf', 'ThreadFix', config, extra_conf_opts=extra_conf_opts)

    def call_api(self, target, method=URLRequest.GET, args={}, call_headers={}, auth_mode='custom'):

        args['apiKey'] = self.config['tf_api_key']
        call_headers['Accept'] = 'application/json'

        if self.config['tf_context_root']:
            target = "%s/%s" % (self.config['tf_context_root'], target)

        try:
            return super(ThreadFixAPI, self).call_api(target, method, args, call_headers, auth_mode)
        except Exception as e:
            raise APIError('API Call failed. Target: %s ; Error: %s' % (target, e))


class ThreadFixIntegrationError(IntegrationError):
    pass


class ThreadFixIntegrator(BaseIntegrator):
    TOOL_NAME = "appscan"
    DEFAULT_MAX_VULNERABILITIES = 10000

    def __init__(self, tf_api, config):
        self.tf_rest_api = tf_api
        self.tf_forms_api = ThreadFixFormsAPI(config)
        self.application_id = None

        config.opts.add("tf_application", "Application name", None, default='')
        config.opts.add("tf_max_vulnerabilities", "Maximum number of expected vulnerabilities from ThreadFix", None,
                        default='%s' % ThreadFixIntegrator.DEFAULT_MAX_VULNERABILITIES)

        super(ThreadFixIntegrator, self).__init__(config, self.TOOL_NAME, [], DEFAULT_MAPPING_FILE)

    def initialize(self):
        super(ThreadFixIntegrator, self).initialize()

        if not self.config['tf_api_key']:
            raise UsageError('Configuration tf_api_key not specified')

        if not self.config['tf_application']:
            raise UsageError('Configuration tf_application not specified')

        try:
            max_count = int(self.config['tf_max_vulnerabilities'])
        except ValueError:
            raise UsageError('Value of tf_max_vulnerabilities should be an integer: %s' %
                             self.config['tf_max_vulnerabilities'])

        if max_count <= 0:
            raise UsageError('Value of tf_max_vulnerabilities should be > 0')

        response = self.tf_rest_api.call_api('rest/teams/')
        if not response['success']:
            raise ThreadFixIntegrationError(response['message'])

        for team in response['object']:
            for application in team['applications']:
                if application['name'] == self.config['tf_application']:
                    self.application_id = application['id']
                    break
        if not self.application_id:
            raise ThreadFixIntegrationError("Application %s not found" % self.config['tf_application'])

    def get_vulnerability_data(self):
        """
        Retrieves vulnerabilities for a given application
        """
        if not self.application_id:
            raise ThreadFixIntegrationError("Application %s not found" % self.config['tf_application'])

        logger.info('Retrieving open vulnerabilities')
        response = self.tf_forms_api.call_api('rest/vulnerabilities/',  method=URLRequest.POST, args={
            'applications[0].id': self.application_id,
            'showOpen': True,
            'showFalsePositive': False,
            'showClosed': False,
            'numberVulnerabilities': self.config['tf_max_vulnerabilities']
        })
        if not response['success']:
            raise ThreadFixIntegrationError(response['message'])

        return response['object']

    def parse(self):
        logger.info('Fetching vulnerability information')
        data = self.get_vulnerability_data()

        if not data:
            return

        channel_name = data[0]['channelNames'][0]

        logger.info('Parsing vulnerability information')
        self.findings = data
        self.report_id = '%s: %s' % (channel_name, self.config['tf_application'])

    def _make_finding(self, item):
        return {
            'weakness_id': str(item['genericVulnerability']['id']),
            'count': 1,
            'description': item['genericVulnerability']['name'],
        }

    def generate_findings(self):
        return [self._make_finding(item) for item in self.findings]
