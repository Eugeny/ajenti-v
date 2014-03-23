import os

from ajenti.api import *
from ajenti.plugins.services.api import ServiceMultiplexor
from ajenti.plugins.vh.api import ApplicationGatewayComponent
from ajenti.util import platform_select


TEMPLATE_CONFIG_FILE = """
[global]
pid = /var/run/php5-fpm.pid
error_log = /var/log/php5-fpm.log

[global-pool]
user = www-data
group = www-data
listen = /var/run/php-fcgi.sock

pm = dynamic
pm.start_servers = 1
pm.max_children = 5
pm.min_spare_servers = 1
pm.max_spare_servers = 5

%(pools)s
"""

TEMPLATE_POOL = """
[%(name)s]
user = www-data
group = www-data

listen = /var/run/php-fcgi-%(name)s.sock

pm = dynamic
pm.max_children = %(max)s
pm.start_servers = %(min)s
pm.min_spare_servers = %(sp_min)s
pm.max_spare_servers = %(sp_max)s

"""


@plugin
class PHPFPM (ApplicationGatewayComponent):
    id = 'php-fcgi'
    title = 'PHP FastCGI'

    def init(self):
        self.config_file = platform_select(
            debian='/etc/php5/fpm/php-fpm.conf',
            centos='/etc/php-fpm.conf',
        )

    def __generate_pool(self, backend, name):
        pm_min = backend.params.get('pm_min', 1) or 1
        pm_max = backend.params.get('pm_max', 5) or 5
        return TEMPLATE_POOL % {
            'name': name,
            'min': pm_min,
            'max': pm_max,
            'sp_min': min(2, pm_min),
            'sp_max': min(6, pm_max),
        }

    def __generate_website(self, website):
        i = 0
        r = ''
        for location in website.locations:
            if location.backend.type == 'php-fcgi':
                i += 1
                location.backend.id = website.slug + '-php-fcgi-' + str(i)
                r += self.__generate_pool(location.backend, location.backend.id)
        return r

    def create_configuration(self, config):
        if os.path.exists(self.config_file):
            os.unlink(self.config_file)
        cfg = TEMPLATE_CONFIG_FILE % {
            'pools': '\n'.join(self.__generate_website(_) for _ in config.websites if _.enabled)
        }
        open(self.config_file, 'w').write(cfg)

    def apply_configuration(self):
        s = ServiceMultiplexor.get().get_one(platform_select(
            debian='php5-fpm',
            centos='php-fpm',
        ))
        if not s.running:
            s.start()
        else:
            s.command('reload')
