import ajenti
from ajenti.api import *
from ajenti.plugins import *


info = PluginInfo(
    title='Ajenti VH - Script Installer',
    icon='globe',
    dependencies=[
        PluginDependency('vh'),
        PluginDependency('vh-mysql'),
        PluginDependency('vh-nginx'),
        PluginDependency('vh-php-fpm'),
        PluginDependency('services'),
        PluginDependency('mysql'),
        BinaryDependency('mysql'),
        BinaryDependency('mysqld_safe'),
    ],
)


def init():
    import installer
