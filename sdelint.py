#!/usr/bin/python
#
# Version 0.3
# Ehsan Foroughi
# Copyright SDElements Inc
#

import sys
import os
import re
import base64
import getpass
import urllib
import urllib2
import optparse
import ConfigParser
import pdb

try:
    import json
except ImportError:
    import json_compat as json

DEFAULT_CONFIG_FILE = "~/.sdelint.cnf"
LINE_SEP_RE = re.compile('\n')
SHOW_LINES = 1


class URLRequest(urllib2.Request):
    GET = 'GET'
    POST = 'POST'
    PUT = 'PUT'
    DELETE = 'DELETE'

    def __init__(self, url, data=None, headers={},
                 origin_req_host=None, unverifiable=False, method=None):
       urllib2.Request.__init__(self, url, data, headers, origin_req_host, unverifiable)
       self.method = method

    def get_method(self):
        if self.method:
            return self.method

        return urllib2.Request.get_method(self)


def show_error(err_msg, usage_hint=False):
    print "FATAL ERROR: %s" % (err_msg)
    if usage_hint:
        print "Try -h to see the usage"
    print

def parseArgs(arvg):
    usage = "%prog [options...] target1 [target2 ...]\n\ntarget(s) are the directory/file to be scanned."

    parser = optparse.OptionParser(usage)
    parser.add_option('-i', '--cnf', metavar='CONF_FILE', dest='cnf', 
        help = "Location of config file. Note that command line values bypass the values specified in the config file.", type='string')
    parser.add_option('-I', '--noninteractive', dest='interactive', default=True, action='store_false', help="Run in Non-Interactive mode")
    parser.add_option('-e', '--email', metavar='EMAIL', dest='username', default='', type='string',
        help = "Username for SDE Accout")
    parser.add_option('-p', '--password', metavar='PASSWORD', dest='password', default='', type='string',
        help = "Password for SDE Accout")
    parser.add_option('-P', '--askpasswd', dest='askpasswd', default=False, action='store_true',
        help = "Prompt for SDE Accout password (interactive mode only)")
    parser.add_option('-s', '--server', dest='server', default='', help="SDE Server instance to use")
    parser.add_option('-a', '--application', dest='application', default='', help="SDE Application to use")
    parser.add_option('-j', '--project', dest='project', default='', help="SDE Project to use")
    parser.add_option('-H', '--skiphidden', dest='skip_hidden', default=True, action='store_false',
        help = "Skip hidden files/directories.")
    parser.add_option('-d', '--debug', metavar='LEVEL', dest='debug_level', default=0, type='int',
        help = "Set debug level (Default is 0, i.e. show no debug messages)")

    try:
        (opts, args) = parser.parse_args()
    except:
        if (str(sys.exc_info()[1]) == '0'):
            # This happens when -h is used
            return
        else:
            show_error("Invalid options specified.", usage_hint=True)
            return

    if (len(args) < 1):
        show_error("Missing target (e.g. use \".\" for current dir)", usage_hint=True)
        return

    for path in args:
        if not os.path.exists(path):
            show_error("Unable to locate or access the path: %s" % path)
            return

    retval = {}
    retval['targets'] = args
    retval['debug_level'] = opts.debug_level
    retval['skip_hidden'] = opts.skip_hidden
    retval['server'] = opts.server
    retval['username'] = opts.username
    retval['interactive'] = opts.interactive
    retval['password'] = None
    retval['askpasswd'] = opts.askpasswd
    if (not retval['interactive']) and (retval['askpasswd']):
        show_error("Password can not be asked in Non-Interactive mode", usage_hint=True)
        return
    if not opts.askpasswd:
        retval['password'] = opts.password
    retval['application'] = opts.application
    retval['project'] = opts.project

    return retval

class Content:
    def __init__(self, connector):
        self.content = {}
        self.ctxrules = []
        self.connector = connector

    def import_context_rules(self, ctx_rules, refid):
        for ctx_item in ctx_rules:
            self.content[refid]['ctxrules'].append(len(self.ctxrules))
            ctx_item['ref'] = refid
            self.ctxrules.append(ctx_item)
            for stype in ['required', 'excluded']:
                for ctx in ctx_item[stype]:
                    if ctx['type'] == 'regex':
                        ctx['regex_val'] = ctx['value']
                        ctx['regex'] = re.compile(ctx['value'])
                    elif ctx['type'] == 'import':
                        rr = 'import\\s+(%s|%s\.\*)' % (ctx['value'], ctx['value'].rsplit('*', 1)[0])
                        ctx['regex_val'] = rr
                        ctx['regex'] = re.compile(rr)

    def import_task_list(self, task_list):
        self.content = {}
        self.ctxrules = []
        for task in task_list:
            tid = task['id'].rsplit('-', 1)[-1]
            self.content[tid] = {'title':task['title'], 'ctxrules':[], 'type':'task', 'howtos':[]}
            self.import_context_rules(task['contextrulesets'], tid)
            for howto in task['implementations']:
                hid = howto['id']
                self.content[hid] = {'title':howto['title'], 'ctxrules':[], 'type':'howto', 'task':tid}
                self.content[tid]['howtos'].append(hid)
                self.import_context_rules(howto['contextrulesets'], hid)
        return self

    def get_task_by_ref(self, ref):
        if ref not in self.content:
            return None
        item = self.content[ref]
        if item['type'] == 'howto':
            return self.get_task_by_ref(item['task'])
        else:
            return ref

class ServerConnector:
    def __init__(self, config):
        self.config = config
        self.base_uri = 'https://%s/api' % (self.config['server'])
        self.app = None
        self.prj = None
        self.auth_mode = 'basic'
        self.session_info = None

    def call_api(self, target, method=URLRequest.GET, args=None):
        req_url = '%s/%s' % (self.base_uri, target)
        if not args:
            args = {}
        data = None
        if method == URLRequest.GET:
            if args:
                req_url = '%s?%s' % (req_url, urllib.urlencode(args))
        else:
            data = json.dumps(args)
        req = URLRequest(req_url, data=data, method=method)
        if target == 'session':
            pass
        elif self.auth_mode == 'basic':
            encoded_auth = base64.encodestring('%s:%s' % (self.config['username'], self.config['password']))[:-1]
            authheader =  "Basic %s" % (encoded_auth)
            req.add_header("Authorization", authheader)
        elif self.auth_mode == 'session':
            if not self.session_info:
                return -105, 'Session not setup or invalid'
            req.add_header('Cookie', '%s=%s' % (self.session_info['session-cookie-name'], self.session_info['session-token']))
            if method != URLRequest.GET:
                req.add_header(self.session_info['csrf-header-name'], self.session_info['csrf-token'])
        else:
            return -103, 'Unknown Authentication mode.'

        try:
            handle = urllib2.urlopen(req)
        except IOError, e:
            if not hasattr(e, 'code'):
                return -101, 'Invalid server or server unreachable.'
            if e.code == 401:
                return e.code, 'Invalid Email/Password.'
            return e.code, 'Unknown Error'

        result = ''
        while True:
            res_buf = handle.read()
            if not res_buf:
                break
            result += res_buf
        handle.close()

        try:
            result = json.loads(result)
        except:
            return -102, 'Unable to process JSON data.'

        return 0, result

    def start_session(self):
        args = {
            'username': self.config['username'],
            'password': self.config['password']}
        ret_stat, ret_val = self.call_api('session', URLRequest.PUT, args=args)
        for key in ['session-cookie-name', 'csrf-token', 'csrf-header-name', 
            'csrf-cookie-domain', 'csrf-cookie-name', 'session-token']:
            if key not in ret_val:
                return -104, 'Invalid session information structure.'
        self.session_info = ret_val
        #self.auth_mode = 'session'
        return 0, 'Session established.'

    def select_application(self):
        args = {}
        if self.config['application']:
            args['name'] = self.config['application']
        ret_stat, ret_val = self.call_api('applications', args=args)
        if ret_stat != 0:
            return ret_stat, ret_val
        app_list = ret_val['applications']

        if (self.config['application']):
            if (not app_list):
                return -1, 'Specified Application not found -> %s' % (self.config['application'])
            elif (len(app_list) == 1):
                return 0, app_list[0]

        if (not self.config['interactive']):
            return -1, 'Missing Application (either use Interactive mode, or specify the exact name of an Application)'

        if (not app_list):
            return -1, 'No Applications to choose from'

        sel_app = None
        while sel_app is None:
            for app_ind in xrange(len(app_list)):
                app = app_list[app_ind]
                print "%2d. %s" % (app_ind+1, app['name'])
            while True:
                print
                print "Enter the Application number you want to select\n Tip: Enter empty to show the Application list again"
                sel_ind = raw_input()
                if not sel_ind:
                    break
                if (not sel_ind.isdigit()) or (int(sel_ind) <= 0) or (int(sel_ind) > len(app_list)):
                    print "Invalid entry, please try again"
                    continue
                sel_app = app_list[int(sel_ind)-1]
                break

        return 0, sel_app

    def _select_project_from_list(self, prj_list):
        while True:
            print " 0. <Select a different Application>"
            for prj_ind in xrange(len(prj_list)):
                prj = prj_list[prj_ind]
                print "%2d. %s" % (prj_ind+1, prj['name'])
            while True:
                print
                print "Enter the Project number you want to select\n Tip: Enter empty to show the Project list again, or Enter 0 to select a different Application"
                sel_ind = raw_input()
                if not sel_ind:
                    break
                if (not sel_ind.isdigit()) or (int(sel_ind) > len(prj_list)):
                    print "Invalid entry, please try again"
                    continue
                if sel_ind == '0':
                    return None
                return prj_list[int(sel_ind)-1]

    def select_project(self):
        while True:
            ret_stat, ret_val = self.select_application()
            if ret_stat != 0:
                return ret_stat, ret_val
            sel_app = ret_val

            args = {'application':sel_app['id']}
            if self.config['project']:
                args['name'] = self.config['project']
            ret_stat, ret_val = self.call_api('projects', args=args)
            if ret_stat != 0:
                return ret_stat, ret_val
            prj_list = ret_val['projects']

            if (self.config['project']):
                if (not prj_list):
                    return -1, 'Specified Project not found -> %s' % (self.config['project'])
                elif (len(prj_list) == 1):
                    return 0, (sel_app, prj_list[0])

            if (not self.config['interactive']):
                return -1, 'Missing Project (either use Interactive mode, or specify the exact name of an Project)'

            sel_prj = self._select_project_from_list(prj_list)
            if sel_prj is not None:
                return 0, (sel_app, sel_prj)

    def get_task_list(self):
        ret_stat, ret_val = self.select_project()
        if ret_stat != 0:
            return ret_stat, ret_val
        self.app, self.prj = ret_val
        
        ret_stat, ret_val = self.call_api('tasks', args={'project':self.prj['id']})
        if ret_stat != 0:
            return ret_stat, ret_val
        task_list = ret_val['tasks']

        return 0, task_list

    def get_compile_task_list(self):
        ret_stat, ret_val = self.get_task_list()
        if ret_stat != 0:
            return ret_stat, ret_val
        task_list = ret_val

        return 0, Content(self).import_task_list(task_list)

class FileScanner:
    def __init__(self, config, content, file_path):
        self.config = config
        self.content = content
        self.file_path = file_path
        self.file_name = self.file_path.rsplit('/', 1)[-1]
        self.file_type = ''
        if '.' in self.file_name:
            self.file_type = self.file_name.rsplit('.', 1)[-1]
        self.match_list = {}
        self.fval = None
        self.line_info = []

    def load_file(self):
        try:
            fp = open(self.file_path, 'r')
        except:
            return False
        self.fval = fp.read(1024*1024)

        line_start_pos = 0
        line_number = 1
        for x in LINE_SEP_RE.finditer(self.fval):
            self.line_info.append((line_start_pos, x.start(), line_number))
            line_start_pos = x.end()
            line_number += 1

        fp.close()
        return True

    def locate_regex(self, regex):
        match = regex.search(self.fval)
        if not match:
            return None
        if not self.line_info:
            return None

        pattern_start, pattern_end = match.span()
        start_line = 1
        end_line = len(self.line_info)
        for start_pos, end_pos, line_number in self.line_info:
            if end_pos >= pattern_start:
                start_line = max(line_number-SHOW_LINES, 1)
                break
        for start_pos, end_pos, line_number in reversed(self.line_info):
            if start_pos <= pattern_end:
                end_line = min(line_number+SHOW_LINES+1, len(self.line_info))
                break
        ret = []
        #print start_line, end_line, pattern_start, pattern_end
        for start_pos, end_pos, line_number in self.line_info[start_line-1:end_line-1]:
            ret.append((line_number, self.fval[start_pos:end_pos]))
        return ret

    def scan(self):
        if self.fval is None:
            stat = self.load_file()
            if not stat:
                return None

        for ctxset in self.content.ctxrules:
            matched_file = True
            matched_reason = []
            for ctx in ctxset['required']:
                if (ctx['type'] == 'file-type'):
                    if (self.file_type == ctx['value']):
                        matched_reason.append("File Type is %s" % ctx['value'])
                    else:
                        matched_file = False
                        break
                elif (ctx['type'] == 'file-name'):
                    if (self.file_name == ctx['value']):
                        matched_reason.append("File Name is %s" % ctx['value'])
                    else:
                        matched_file = False
                        break
                elif (ctx['type'] in ['import', 'regex']):
                    match = self.locate_regex(ctx['regex'])
                    if match:
                        match = ['%7d: %s' % (x[0], x[1]) for x in match]
                        matched_reason.append("Pattern '%s' found below:\n%s" % (ctx['regex_val'], '\n'.join(match)))
                    else:
                        matched_file = False
                        break
                else:
                    matched_file = False
                    break
            if not matched_file:
                continue
            for ctx in ctxset['excluded']:
                if (ctx['type'] == 'file-type'):
                    if (self.file_type != ctx['value']):
                        matched_reason.append("File Type is NOT %s" % ctx['value'])
                    else:
                        matched_file = False
                        break
                elif (ctx['type'] == 'file-name'):
                    if (self.file_name != ctx['value']):
                        matched_reason.append("File Name is NOT %s" % ctx['value'])
                    else:
                        matched_file = False
                        break
                else:
                    print ctxset
                    matched_file = False
                    break
            if matched_file:
                task_ref = self.content.get_task_by_ref(ctxset['ref'])
                if task_ref not in self.match_list:
                    self.match_list[task_ref] = []
                self.match_list[task_ref].append(' AND '.join(matched_reason))
        if self.match_list:
            print "====================================="
            print "Tasks for file %s:" % (self.file_path)
            for item in self.match_list:
                print "  %s" % (self.content.content[item]['title'])
                print "  Reasons: %s" % (self.match_list[item][0])
                print
                    
        return

class Scanner:
    def __init__(self, config, content):
        self.config = config
        self.content = content

    def read_config(self):
        cnf = ConfigParser.ConfigParser()
        cnf.read(self.config['cnf'])
        self.ID = cnf.get('mysqld', 'server-id')

    def scan_file(self, file_path):
        file_scanner = FileScanner(self.config, self.content, file_path)
        file_scanner.scan()

    def scan(self):
        for target in self.config['targets']:
            for (dirpath, dirnames, filenames) in os.walk(target):
                if self.config['skip_hidden']:
                    for dirname in reversed(dirnames):
                        if dirname.startswith('.'):
                            dirnames.remove(dirname)
                for file_name in filenames:
                    file_path = os.path.join(dirpath, file_name)
                    file_scanner = FileScanner(self.config, self.content, file_path)
                    file_scanner.scan()

def load(config):
    while True:
        if config['askpasswd']:
            print "Enter the password for account: %s" % (config['username'])
            config['password'] = getpass.getpass()
        connector = ServerConnector(config)
        ret_stat, ret_val = connector.start_session()
        ret_stat, ret_val = connector.get_compile_task_list()
        if ret_stat == 0:
            content = ret_val
            break
        elif ret_stat == 401:
            if config['askpasswd']:
                print "Password Error\n"
                continue
            show_error('Invalid Email/Password')
        elif ret_stat == -1:
            show_error(ret_val)
        else:
            show_error('Unexpected Error - code %s: %s' % (ret_stat, ret_val))
        sys.exit(1)
    return content 

def main(argv):
    cmd_line_args = parseArgs(argv)
    if cmd_line_args is None:
        sys.exit(1)

    handler = urllib2.HTTPSHandler(debuglevel=cmd_line_args['debug_level'])
    opener = urllib2.build_opener(handler)
    urllib2.install_opener(opener)

    content = load(cmd_line_args)

    scanner = Scanner(cmd_line_args, content)
    scanner.scan()

if __name__ == "__main__":
    main(sys.argv)

