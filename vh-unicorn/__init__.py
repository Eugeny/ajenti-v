import ajenti
from ajenti.api import *
from ajenti.plugins import *


info = PluginInfo(
    title='Ajenti VH - Unicorn Support',
    icon='globe',
    dependencies=[
        PluginDependency('vh'),
        PluginDependency('services'),
        PluginDependency('supervisor'),
        BinaryDependency('unicorn_rails'),
    ],
)


def init():
    from ajenti.plugins.vh import destroyed_configs
    destroyed_configs.append('unicorn')

    import unicorn
