import ajenti
from ajenti.api import *
from ajenti.plugins import *
from ajenti.util import platform_select


info = PluginInfo(
    title='Ajenti VH - PHP 7.0-FPM Support',
    icon='globe',
    dependencies=[
        PluginDependency('vh'),
        PluginDependency('services'),
        BinaryDependency('php-fpm7.0'),
    ],
)


def init():
    from ajenti.plugins.vh import destroyed_configs
    destroyed_configs.append('php7.0-fpm')

    import php70fpm
