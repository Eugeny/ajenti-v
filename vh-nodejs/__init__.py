from ajenti.api import *
from ajenti.plugins import *


info = PluginInfo(
    title='Ajenti VH - Node.JS Support',
    icon='globe',
    dependencies=[
        PluginDependency('vh'),
        PluginDependency('services'),
        PluginDependency('supervisor'),
    ],
)


def init():
    import nodejs
