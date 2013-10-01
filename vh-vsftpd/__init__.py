import ajenti
from ajenti.api import *
from ajenti.plugins import *


info = PluginInfo(
    title='Ajenti VH - VSFTPD Support',
    icon='globe',
    dependencies=[
        PluginDependency('vh'),
        PluginDependency('services'),
        BinaryDependency('vsftpd'),
    ],
)


def init():
    from ajenti.plugins.vh import destroyed_configs
    destroyed_configs.append('vsftpd')

    import vsftpd
