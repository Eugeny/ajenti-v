import os
import shutil
import subprocess

from ajenti.api import *
from ajenti.plugins.services.api import ServiceMultiplexor
from ajenti.plugins.vh.api import WebserverComponent, SanityCheck, Restartable

from nginx_templates import *


@plugin
class NginxConfigTest (SanityCheck):
    def init(self):
        self.type = _('NGINX config test')

    def check(self):
        p = subprocess.Popen(['nginx', '-t'], stderr=subprocess.PIPE)
        o, self.message = p.communicate()
        return p.returncode == 0


@plugin
class NginxServiceTest (SanityCheck):
    def init(self):
        self.type = _('NGINX service')

    def check(self):
        return ServiceMultiplexor.get().get_one('nginx').running


@plugin
class NginxWebserver (WebserverComponent):
    def init(self):
        self.config_root = '/etc/nginx'
        self.config_file = '/etc/nginx/nginx.conf'
        self.config_file_mime = '/etc/nginx/mime.conf'
        self.config_file_fastcgi = '/etc/nginx/fcgi.conf'
        self.config_file_proxy = '/etc/nginx/proxy.conf'
        self.config_vhost_root = '/etc/nginx/conf.d'
        self.config_custom_root = '/etc/nginx.custom.d'

    def __generate_website_location(self, ws, location):
        params = location.backend.params

        if location.backend.type == 'static':
            content = TEMPLATE_LOCATION_CONTENT_STATIC % {
                'autoindex': 'autoindex on;' if params['autoindex'] else '',
            }

        if location.backend.type == 'proxy':
            content = TEMPLATE_LOCATION_CONTENT_PROXY % {
                'url': params.get('url', 'http://127.0.0.1/'),
            }

        if location.backend.type == 'fcgi':
            content = TEMPLATE_LOCATION_CONTENT_FCGI % {
                'url': params.get('url', '127.0.0.1:9000'),
            }

        if location.backend.type == 'php-fcgi':
            content = TEMPLATE_LOCATION_CONTENT_PHP_FCGI % {
                'id': location.backend.id,
            }

        if location.backend.type == 'python-wsgi':
            content = TEMPLATE_LOCATION_CONTENT_PYTHON_WSGI % {
                'id': location.backend.id,
            }

        if location.backend.type == 'ruby-unicorn':
            content = TEMPLATE_LOCATION_CONTENT_RUBY_UNICORN % {
                'id': location.backend.id,
            }

        if location.backend.type == 'ruby-puma':
            content = TEMPLATE_LOCATION_CONTENT_RUBY_PUMA % {
                'id': location.backend.id,
            }

        if location.backend.type == 'nodejs':
            content = TEMPLATE_LOCATION_CONTENT_NODEJS % {
                'port': location.backend.params.get('port', 8000) or 8000,
            }

        if location.custom_conf_override:
            content = ''

        path_spec = ''
        if location.path:
            if location.path_append_pattern:
                path_spec = 'root %s;' % location.path
            else:
                path_spec = 'alias %s;' % location.path

        return TEMPLATE_LOCATION % {
            'pattern': location.pattern,
            'custom_conf': location.custom_conf,
            'path': path_spec,
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
            'ports': (
                '\n'.join(
                    'listen %s:%s%s%s%s;' % (
                        x.host, x.port,
                        ' ssl' if x.ssl else '',
                        ' spdy' if x.spdy else '',
                        ' default_server' if x.default else '',
                    )
                    for x in website.ports
                )
            ),
            'ssl_cert': 'ssl_certificate %s;' % website.ssl_cert_path if website.ssl_cert_path else '',
            'ssl_key': 'ssl_certificate_key %s;' % website.ssl_key_path if website.ssl_key_path else '',
            'maintenance': TEMPLATE_MAINTENANCE if website.maintenance_mode else '',
            'root': website.root,
            'custom_conf': website.custom_conf,
            'custom_conf_toplevel': website.custom_conf_toplevel,
            'locations': (
                '\n'.join(self.__generate_website_location(website, location) for location in website.locations)
            ) if not website.maintenance_mode else '',
        }
        return TEMPLATE_WEBSITE % params

    def create_configuration(self, config):
        shutil.rmtree(self.config_root)
        os.mkdir(self.config_root)
        os.mkdir(self.config_vhost_root)

        if not os.path.exists(self.config_custom_root):
            os.mkdir(self.config_custom_root)

        open(self.config_file, 'w').write(TEMPLATE_CONFIG_FILE)
        open(self.config_file_mime, 'w').write(TEMPLATE_CONFIG_MIME)
        open(self.config_file_fastcgi, 'w').write(TEMPLATE_CONFIG_FCGI)
        open(self.config_file_proxy, 'w').write(TEMPLATE_CONFIG_PROXY)

        for website in config.websites:
            if website.enabled:
                open(os.path.join(self.config_vhost_root, website.slug + '.conf'), 'w')\
                    .write(self.__generate_website_config(website))

    def apply_configuration(self):
        NGINXRestartable.get().schedule()

    def get_checks(self):
        return [NginxConfigTest.new(), NginxServiceTest.new()]


@plugin
class NGINXRestartable (Restartable):
    def restart(self):
        s = ServiceMultiplexor.get().get_one('nginx')
        if not s.running:
            s.start()
        else:
            s.command('reload')
