import uuid

from ajenti.api import *
from ajenti.ui import on
from ajenti.ui.binder import Binder

from ajenti.plugins.mysql.api import MySQLDB
from ajenti.plugins.db_common.api import Database, User
from ajenti.plugins.vh.extensions import BaseExtension


@plugin
class MySQLExtension (BaseExtension):
    default_config = {
        'created': False,
        'name': None,
        'user': None,
        'password': None,
    }
    name = 'MySQL'

    def init(self):
        self.append(self.ui.inflate('vh-mysql:ext'))
        self.binder = Binder(self, self)
        self.refresh()
        self.db = MySQLDB.get()

    @staticmethod
    def selftest():
        try:
            MySQLDB.get().query_databases()
        except:
            pass

    def refresh(self):
        self.binder.setup().populate()
        self.find('db-name').value = self.website.slug
        self.find('db-username').value = self.website.slug
        
    def update(self):
        self.binder.update()

    def on_destroy(self):
        if self.config['created']:
            self.on_delete()

    @on('create', 'click')
    def on_create(self):
        try:
            self.db.query_databases()
        except Exception, e:
            self.context.notify('error', str(e))
            self.context.launch('configure-plugin', plugin=self.db)
            return

        dbname = self.find('db-name').value
        username = self.find('db-username').value

        for db in self.db.query_databases():
            if db.name == dbname:
                self.context.notify('error', _('This database name is already used'))
                return
        
        for user in self.db.query_users():
            if user.name == username:
                self.context.notify('error', _('This username is already used'))
                return

        self.config['name'] = dbname
        self.config['username'] = username
        self.config['password'] = str(uuid.uuid4())
        
        try:
            self.db.query_create(self.config['name'])
        except Exception, e:
            self.context.notify('error', str(e))
            return

        self.config['created'] = True

        db = Database()
        db.name = self.config['name']

        user = User()
        user.name = self.config['username']
        user.password = self.config['password']
        user.host = 'localhost'
        try:
            self.db.query_create_user(user)
        except Exception, e:
            self.db.query_drop(db)
            self.context.notify('error', str(e))
            return

        self.db.query_grant(user, db)
        self.refresh()

        self.context.notify('info', _('Database created. Click Save to save the database info.'))

    @on('delete', 'click')
    def on_delete(self):
        db = Database()
        db.name = self.config['name']
        try:
            self.db.query_drop(db)
        except Exception, e:
            # I'm gonna burn in hell for this...
            if not 'ERROR 1008' in e:
                raise e
        
        user = User()
        user.name = self.config['username']
        user.host = 'localhost'
        
        try:
            self.db.query_drop_user(user)
        except Exception, e:
            if not 'ERROR 1008' in e:
                raise e
        self.config['created'] = False
        self.refresh()
