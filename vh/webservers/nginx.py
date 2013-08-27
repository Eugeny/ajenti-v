import os
import shutil

from ajenti.api import *
from ajenti.plugins.services.api import ServiceMultiplexor

from nginx_templates import *


@plugin
class NginxWebserver (object):
    def init(self):
        self.config_root = '/etc/nginx'
        self.config_file = '/etc/nginx/nginx.conf'
        self.config_file_mime = '/etc/nginx/mime.conf'
        self.config_file_fastcgi = '/etc/nginx/fcgi.conf'
        self.config_file_proxy = '/etc/nginx/proxy.conf'
        self.config_vhost_root = '/etc/nginx/conf.d'

    def __generate_website_config(self, website):
        params = {
            'server_name': (
                'server_name %s;' % (' '.join(domain.domain for domain in website.domains))
            ) if website.domains else '',
            'maintenance': TEMPLATE_MAINTENANCE if website.maintenance_mode else '',
            'locations': '',
        }
        return TEMPLATE_WEBSITE % params

    def create_configuration(self, config):
        shutil.rmtree(self.config_root)
        os.mkdir(self.config_root)
        os.mkdir(self.config_vhost_root)
        open(self.config_file, 'w').write(TEMPLATE_CONFIG_FILE)
        open(self.config_file_mime, 'w').write(TEMPLATE_CONFIG_MIME)
        open(self.config_file_fastcgi, 'w').write(TEMPLATE_CONFIG_FCGI)
        open(self.config_file_proxy, 'w').write(TEMPLATE_CONFIG_PROXY)

        for website in config.websites:
            if website.enabled:
                open(os.path.join(self.config_vhost_root, website.slug + '.conf'), 'w')\
                    .write(self.__generate_website_config(website))

    def apply_configuration(self):
        ServiceMultiplexor.get().get_one('nginx').command('reload')
