from ajenti.api import *
from ajenti.ui import UIElement


@interface
class BaseExtension (UIElement):
    typeid = 'vh:extension'
    default_config = None

    def __init__(self, ui, website, config=None):
        UIElement.__init__(self, ui)
        self.editor_ui = None
        self.website = website
        self.config = config or self.default_config.copy()

    @staticmethod
    def selftest():
        pass

    def update(self):
        pass

    def on_destroy(self):
        pass
