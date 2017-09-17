import ajenti
from ajenti.api import *
from ajenti.plugins import *
from ajenti.util import platform_select


info = PluginInfo(
    title='Ajenti VH - PHP 7.1-FPM Support',
    icon='globe',
    dependencies=[
        PluginDependency('vh'),
        PluginDependency('services'),
        BinaryDependency('php-fpm7.1'),
    ],
)


def init():
    from ajenti.plugins.vh import destroyed_configs
    destroyed_configs.append('php7.1-fpm')

    import php71fpm
