import logging

class LoggerModules:
    """
    This initializes the loggers and provides an easy control for setting log levels.
    """
    def __init__(self):
        self.modules = []
        self.default_level = logging.WARNING

    def add_mod(self, modname):
        if modname in self.modules:
            return
        self.modules.append(modname)
        self.set_level(modname, self.default_level)

    def set_level(self, modname, level):
        if modname not in self.modules:
            raise KeyError, modname
        logger = logging.getLogger(modname)
        logger.setLevel(level)

    def set_all_level(self, level):
        self.default_level = level
        for modname in self.modules:
            self.set_level(modname, level)


mods = LoggerModules()

mods.add_mod('') # Root handler

# Setting default handlers for all library modules
import sdelib
for modname in sdelib.__all__:
    mods.add_mod('%s.%s' % (__name__.rsplit('.', 1)[0], modname))

console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter('%(levelname)s - %(name)s - %(message)s'))
root_logger = logging.getLogger()
root_logger.addHandler(console_handler)
