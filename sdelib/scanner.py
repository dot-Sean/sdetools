import re
import os

from commons import UsageError

LINE_SEP_RE = re.compile('\n')
SHOW_LINES = 1

class FileScanner:
    def __init__(self, config, content, file_path):
        self.config = config
        self.content = content
        self.file_path = file_path
        self.file_name = os.path.basename(self.file_path)
        self.file_type = os.path.splitext(self.file_name)[1].lstrip('.')
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
            print "====================================================="
            print "Tasks for file %s:" % (self.file_path)
            for item in self.match_list:
                print "  %s" % (self.content.content[item]['title'])
                print "  Reasons: %s" % (self.match_list[item][0])
                print

        return

class Scanner:
    def __init__(self, config):
        self.config = config
        self.content = None

    def validate_args(self, args):
        """
        Validator helper for argument parsing. Returns error description in case of error,
        or None if validate passed.
        """
        if not args:
            return "Missing target (e.g. use \".\" for current dir)"

        for path in args:
            if not os.path.exists(path):
                return "Unable to locate or access the path: %s" % (path)

        return None

    def set_content(self, content):
        self.content = content

    def scan_file(self, file_path):
        if self.content is None:
            raise UsageError('Missing content: Set content before using scanner.')
        file_scanner = FileScanner(self.config, self.content, file_path)
        file_scanner.scan()

    def scan(self):
        if self.content is None:
            raise UsageError('Missing content: Set content before using scanner.')
        file_paths = []
        for target in self.config['targets']:
            if not os.path.isdir(target):
                file_paths.append(target)
                continue
            for (dirpath, dirnames, filenames) in os.walk(target):
                if self.config['skip_hidden']:
                    for dirname in reversed(dirnames):
                        if dirname.startswith('.'):
                            dirnames.remove(dirname)
                for file_name in filenames:
                    file_path = os.path.join(dirpath, file_name)
                    file_paths.append(file_path)

        for file_path in file_paths:
            print "=== Scanning: %s ===" % (file_path.ljust(35))
            file_scanner = FileScanner(self.config, self.content, file_path)
            file_scanner.scan()
