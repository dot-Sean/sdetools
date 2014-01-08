from sdetools.sdelib.cmd import BaseCommand

from sdetools.modules.sync_github.github_plugin import GitHubConnector, GitHubAPI

class Command(BaseCommand):
    help = 'GitHub <-> SDE sync utility.'

    def configure(self):
        alm_api = GitHubAPI(self.config)
        self.github = GitHubConnector(self.config, alm_api)

    def handle(self):
        self.github.initialize()
        self.github.synchronize()
        return True
