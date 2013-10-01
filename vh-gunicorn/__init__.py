import ajenti
from ajenti.api import *
from ajenti.plugins import *


info = PluginInfo(
    title='Ajenti VH - GUnicorn Support',
    icon='globe',
    dependencies=[
        PluginDependency('vh'),
        PluginDependency('services'),
        BinaryDependency('gunicorn'),
    ],
)


def init():
    from ajenti.plugins.vh import destroyed_configs
    destroyed_configs.append('gunicorn')
    destroyed_configs.append('supervisord')

    import gunicorn
