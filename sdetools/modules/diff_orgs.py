import re
import sys

from sdetools.sdelib.cmd import BaseCommand
from sdetools.sdelib.sdeapi import APIBase


class Command(BaseCommand):
    name = 'diff_orgs'
    help = 'Outputs if two orgs match'

    def configure(self):
        self.config.opts.add('sde_application', "Chosen application name", default='')
        self.config.opts.add('sde_user', "Base server user", default='')
        self.config.opts.add('sde_pass', "Base server password", default='')
        self.config.opts.add('sde_server', "Base server address", default='')
        self.config.opts.add('sde_method', "Base server address", default='')
        self.config.opts.add('sde_api_token', "Base server Api Token", default='')
        self.config.opts.add('other_sde_api_token', "Specify the other server", default='')

    def get_org_content(self, api_key, application=''):
        content = dict()
        self.config['sde_api_token'] = api_key

        sde_api = APIBase(self.config)
        if application:
            app_list = sde_api.get_applications(name=application)
        else:
            app_list = sde_api.get_applications()

        task_keys_to_remove = ['project', 'id']
        normalized_host = 'https://example.com/'  # normalized host name

        app_count = 0
        for app in app_list:
            app_count = app_count + 1

            prj_list = sde_api.get_projects(app['id'])
            projects = {}
            project_count = 0
            for prj in prj_list:
                project_count = project_count + 1
                print("\rCollecting from %s [%s - %d of %d projects]: %d of %d apps" % (
                    self.config['sde_server'],
                    app['name'],
                    project_count,
                    len(prj_list),
                    app_count,
                    len(app_list)))

                if prj['archived']:
                    continue
                tasks = sde_api.get_tasks(prj['id'])
                for t in tasks:
                    for tk in task_keys_to_remove:
                        if tk in t:
                            del t[tk]
                    # normalize HowTo urls
                    for impl in t['implementations']:
                        impl['url'] = re.sub('https://([^/]+)/', normalized_host, impl['url'])

                    # normalize task url
                    t['url'] = re.sub('https://([^/]+)/', normalized_host, t['url'])

                projects[prj['name']] = {'tasks': tasks}

            content[app['name']] = projects

        return content

    def handle(self):
        base_content = self.get_org_content(self.config['sde_api_token'], self.config['sde_application'])
        other_content = self.get_org_content(self.config['other_sde_api_token'], self.config['sde_application'])

        if base_content == other_content:
            print "Same content"
        else:
            print "Differences detected"

        return True