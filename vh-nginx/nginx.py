import os
import shutil

from ajenti.api import *
from ajenti.plugins.services.api import ServiceMultiplexor
from ajenti.plugins.vh.api import WebserverComponent

from nginx_templates import *


@plugin
class NginxWebserver (WebserverComponent):
    def init(self):
        self.config_root = '/etc/nginx'
        self.config_file = '/etc/nginx/nginx.conf'
        self.config_file_mime = '/etc/nginx/mime.conf'
        self.config_file_fastcgi = '/etc/nginx/fcgi.conf'
        self.config_file_proxy = '/etc/nginx/proxy.conf'
        self.config_vhost_root = '/etc/nginx/conf.d'

    def __generate_website_location(self, ws, location):
        if location.backend.type == 'static':
            params = location.backend.params
            content = TEMPLATE_LOCATION_CONTENT_STATIC % {
                'root': ('root %s;' % params['root']) if params.get('root', '') else '',
                'autoindex': 'autoindex on;' if params['autoindex'] else '',
            }

        if location.backend.type == 'php-fcgi':
            params = location.backend.params
            content = TEMPLATE_LOCATION_CONTENT_PHP_FCGI % {
                'id': location.backend.id,
            }

        if location.backend.type == 'python-wsgi':
            params = location.backend.params
            content = TEMPLATE_LOCATION_CONTENT_PYTHON_WSGI % {
                'id': location.backend.id,
            }

        if location.backend.type == 'ruby-unicorn':
            params = location.backend.params
            content = TEMPLATE_LOCATION_CONTENT_RUBY_UNICORN % {
                'id': location.backend.id,
            }

        return TEMPLATE_LOCATION % {
            'pattern': location.pattern,
            'match': {
                'exact': '',
                'regex': '~',
                'force-regex': '^~',
            }[location.match],
            'content': content,
        }

    def __generate_website_config(self, website):
        params = {
            'slug': website.slug,
            'server_name': (
                'server_name %s;' % (' '.join(domain.domain for domain in website.domains))
            ) if website.domains else '',
            'maintenance': TEMPLATE_MAINTENANCE if website.maintenance_mode else '',
            'root': website.root,
            'locations': (
                '\n'.join(self.__generate_website_location(website, location) for location in website.locations)
            ),
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
        s = ServiceMultiplexor.get().get_one('nginx')
        if not s.running:
            s.start()
        else:
            s.command('reload')
