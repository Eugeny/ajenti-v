import ajenti
from ajenti.api import *
from ajenti.plugins import *


info = PluginInfo(
    title='Ajenti VH - Puma.io Support',
    icon='globe',
    dependencies=[
        PluginDependency('vh'),
        PluginDependency('services'),
        PluginDependency('supervisor'),
        BinaryDependency('bundle'),
    ],
)


def init():
    import puma
