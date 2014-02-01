import ajenti
from ajenti.api import *
from ajenti.plugins import *
from ajenti.util import platform_select


info = PluginInfo(
    title='Ajenti VH - PHP-FPM Support',
    icon='globe',
    dependencies=[
        PluginDependency('vh'),
        PluginDependency('services'),
        BinaryDependency(platform_select(
            debian='php5-fpm',
            default='php-fpm'
        )),
    ],
)


def init():
    from ajenti.plugins.vh import destroyed_configs
    destroyed_configs.append('php-fpm')

    import phpfpm
