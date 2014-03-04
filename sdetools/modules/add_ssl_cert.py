# Copyright SDElements Inc

import ssl
import socket
import re
from sdetools.sdelib.commons import UsageError, Error
from sdetools.sdelib.cmd import BaseCommand
from sdetools.extlib import http_req

SSL_START_MARKER = '-----BEGIN CERTIFICATE-----'
SSL_END_MARKER = '-----END CERTIFICATE-----'

class Command(BaseCommand):
    help = 'Import a self-signed or other SSL certificate to sdetools'

    def configure(self):
        self.config.opts.add('server', "Server to connect to",
                             default='')
        self.config.opts.add('port', "Port to connect to",
                             default='443')
        self.config.opts.add('custom_cert', "Certificate to import",
                             default='')
        #self.config.opts.add('cert_loc', "Location of the Custom Certificate bundle",
        #                     default='')

    def validate_pem(self, certs):
        for x in certs:
            temp = x.splitlines()[1:-1]
            for y in temp:
                if not ((len(y) % 4 == 0) and re.match(r"^[a-zA-Z0-9\+/]*={0,3}$", y)):
                    return x
        return None


    def handle(self):
        if self.config['custom_cert'] == '' or not self.config['custom_cert']:
            # If no custom_cert specified, try fetching the cert from the server
            if self.config['server'] == '' or not self.config['server']:
                raise UsageError('No server specified')
            try:
                self.config['port'] = int(self.config['port'])
            except ValueError:
                raise UsageError('Port number invalid')
            try:
                cert = ssl.get_server_certificate((self.config['server'], self.config['port']))
            except ssl.SSLError, err:
                raise Error('Can not establish SSL connection with the specified server/port.'
                            ' Reason: %s' % (err))
            except socket.error, err:
                raise Error('Unable to reach the specified server.'
                            ' Reason: %s' % (err))
        else:
            if SSL_END_MARKER in self.config['custom_cert']:
                # Use input, if it is a certificate
                cert = self.config['custom_cert']
            else:
                # Try opening the specified certificate
                try:
                    cert = open(self.config['custom_cert']).read()
                except IOError, err:
                    raise Error('Unable to open file. Reason: %s' % (err))

        cert_check = re.compile('(?<=' + SSL_START_MARKER + ').+?(?=' + SSL_END_MARKER + ')', re.S)

        # split custom certificates and remove extra whitespace
        candidates = re.findall(cert_check, cert)
        candidates = map(lambda content: (SSL_START_MARKER + '\n' + content.strip() + '\n' + SSL_END_MARKER + '\n'), candidates)

        if not candidates:
            raise ValueError('No valid certificate(s) found')

        open(http_req.custom_ca_file, 'a').close()

        custom_bundle = open(http_req.custom_ca_file).read()

        # split present certificates and remove extra whitespace
        present_cert = re.findall(cert_check, custom_bundle)
        present_cert = map(lambda content: (SSL_START_MARKER + '\n' + content.strip() + '\n' + SSL_END_MARKER + '\n'), present_cert)

        # select only missing certificates
        import_cert = [x for x in candidates if x not in present_cert]

        validation = self.validate_pem(import_cert)

        if validation:
            raise ValueError('Invalid certificate present: \n%s' % validation)

        fp = open(http_req.custom_ca_file, 'a')
        fp.write(''.join(import_cert))
        fp.close()

        http_req.compile_certs()

        return True
