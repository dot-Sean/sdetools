# Version 0.01
# Copyright SDElements Inc


import csv
import datetime
from sdetools.sdelib.cmd import BaseCommand
from sdetools.sdelib.interactive_plugin import PlugInExperience

from sdetools.sdelib import log_mgr
logger = log_mgr.mods.add_mod(__name__)

DEFAULT_CSV_FILENAME = "output.csv"

def epoch_to_date(val):
    return datetime.datetime.fromtimestamp(val).date()

class Command(BaseCommand):
    help = 'Creates a CSV output of project details for reporting purposes (Proof of Concept only!)'

    def configure(self):
        self.plugin = PlugInExperience(self.config)

        self.config.opts.add("list_archived", "Include Archived Projects (True|False)", 
            default="False")
        self.config.opts.add("list_tasks", "Include Tasks inside each Project (True|FalsE)",
            default="True")
        self.config.opts.add("created_after", "Project Created After (YYYY-MM-DD)", 
            default="1900-01-01")
        self.config.opts.add("created_before", "Project Created Before (YYYY-MM-DD)", 
            default="9999-12-31")
        self.config.opts.add("write_file", "Name of Output File", 'w',
            default=DEFAULT_CSV_FILENAME)
        self.config.opts.add("show_progress", "Show Progress on Console (True|False)",
            default="True")


    def test_report(self, plugin):
        self.config.process_boolean_config('list_archived')
        self.config.process_boolean_config('list_tasks')
        self.config.process_date_config('created_after')
        self.config.process_date_config('created_before')
        self.config.process_boolean_config('show_progress')

        app_list = plugin.api.get_applications()

        csv_file = csv.writer(open(self.config['write_file'], 'wb'))
        header = ['Application', 'Project', 'Created', 'Creator']
        if self.config['list_tasks']:
            header += ['Task', 'Weakness', 'Status']

        csv_file.writerow(header)

        for app_ind in xrange(len(app_list)):
            app = app_list[app_ind]
            if self.config['show_progress']:
                print "Progress: %2d %% - App: %s" % (int(float(app_ind+1)*100/len(app_list)), app['name'])
            logger.info('Going through App: %s' % (app['name']))
            args = {}
            #TODO: Once the server side bug is fixed, use this instead of listing all
            #if not self.config['list_archived']:
            #    args['archived'] = 'false'
            proj_list = plugin.api.get_projects(app['id'], **args)

            for proj_ind in xrange(len(proj_list)):
                proj = proj_list[proj_ind]
                if not self.config['list_archived']:
                    if proj['archived']:
                        continue
                create_date = epoch_to_date(proj['created'])
                if create_date < self.config['created_after']:
                    continue
                if create_date > self.config['created_before']:
                    continue
                logger.info('Going through Project: %s' % (proj['name']))

                row = [app['name'], proj['name'], create_date, proj['creator']]
                if not self.config['list_tasks']:
                    csv_file.writerow(row)
                    continue
                if self.config['show_progress']:
                    print "    Prj (%d / %d): %s" % (proj_ind+1, len(proj_list), proj['name'])

                task_list = plugin.api.get_tasks(proj['id'])

                for task_ind in xrange(len(task_list)):
                    task = task_list[task_ind]
                    csv_file.writerow(row + [task['title'], task['weakness']['title'], task['status']])

    def handle(self):
        self.test_report(self.plugin)
        return True
