import os
import shutil

from ajenti.api import *
from ajenti.plugins.services.api import ServiceMultiplexor
from ajenti.plugins.vh.api import ApplicationGatewayComponent


TEMPLATE_PROCESS = """
CONFIG = {
    'working_dir': '%(root)s',
    'args': {
        '--bind=unix:/var/run/gunicorn-%(id)s.sock',
        %(workers)s
        '%(module)s'
    }
}
"""


@plugin
class Gunicorn (ApplicationGatewayComponent):
    id = 'python-wsgi'
    title = 'Python WSGI'

    def init(self):
        self.config_dir = '/etc/gunicorn.d/'

    def __generate_website(self, website):
        i = 0
        for location in website.locations:
            if location.backend.type == 'python-wsgi':
                i += 1
                location.backend.id = website.slug + '-python-wsgi-' + str(i)
                c = TEMPLATE_PROCESS % {
                    'id': location.backend.id,
                    'workers': ("'--workers=%i'," % location.backend.params['workers']) if location.backend.params['workers'] else '',
                    'module': location.backend.params['module'],
                    'root': website.root,
                }
                open(os.path.join(self.config_dir, location.backend.id.replace('-', '_')), 'w').write(c)

    def create_configuration(self, config):
        shutil.rmtree(self.config_dir)
        os.mkdir(self.config_dir)
        for website in config.websites:
            self.__generate_website(website)

    def apply_configuration(self):
        s = ServiceMultiplexor.get().get_one('gunicorn')
        if not s.running:
            s.start()
        else:
            s.command('reload')
