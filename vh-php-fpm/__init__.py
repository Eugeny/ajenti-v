import ajenti
from ajenti.api import *
from ajenti.plugins import *


info = PluginInfo(
    title='Ajenti VH - PHP-FPM Support',
    icon='globe',
    dependencies=[
        PluginDependency('vh'),
        PluginDependency('services'),
        BinaryDependency('php5-fpm'),
    ],
)


def init():
    from ajenti.plugins.vh import destroyed_configs
    destroyed_configs.append('php-fpm')

    import phpfpm
