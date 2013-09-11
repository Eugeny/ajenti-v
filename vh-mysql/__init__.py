import ajenti
from ajenti.api import *
from ajenti.plugins import *


info = PluginInfo(
    title='Ajenti VH - MySQL Support',
    icon='globe',
    dependencies=[
        PluginDependency('vh'),
        PluginDependency('services'),
        PluginDependency('mysql'),
        BinaryDependency('mysql'),
        BinaryDependency('mysqld'),
    ],
)


def init():
    import mysql
