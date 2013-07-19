from sdetools.sdelib.commons import abc
abstractmethod = abc.abstractmethod

class FortifyBaseImporter(object):

    def __init__(self):
        self.report_id = ""
        self.raw_findings = []

    @abstractmethod
    def _make_raw_finding(self, node):
        pass

    @abstractmethod
    def parse(self):
        pass
