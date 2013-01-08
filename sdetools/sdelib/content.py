import re

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

    def get_task_by_ref(self, ref):
        if ref not in self.content:
            return None
        item = self.content[ref]
        if item['type'] == 'howto':
            return self.get_task_by_ref(item['task'])
        else:
            return ref

