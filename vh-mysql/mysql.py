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
        self.binder.autodiscover()
        self.refresh()
        self.db = MySQLDB.get()

    @staticmethod
    def selftest():
        try:
            MySQLDB.get().query_databases()
        except:
            pass

    def refresh(self):
        self.binder.reset().populate()
        
    def update(self):
        self.binder.update()

    def on_destroy(self):
        if self.config['created']:
            self.on_delete()

    @on('create', 'click')
    def on_create(self):
        self.config['username'] = self.website.slug
        self.config['password'] = str(uuid.uuid4())
        self.config['created'] = True
        self.config['name'] = self.website.slug

        while True:
            exists = False
            for db in self.db.query_databases():
                if db.name == self.config['name']:
                    exists = True
                    break
            if not exists:
                break
            else:
                self.config['name'] += '_'
        
        self.db.query_create(self.config['name'])
        db = Database()
        db.name = self.config['name']

        while True:
            exists = False
            for user in self.db.query_users():
                if user.name == self.config['username']:
                    exists = True
                    break
            if not exists:
                break
            else:
                self.config['username'] += '_'
        
        user = User()
        user.name = self.config['username']
        user.password = self.config['password']
        user.host = 'localhost'
        self.db.query_create_user(user)
        self.db.query_grant(user, db)
        self.refresh()

    @on('delete', 'click')
    def on_delete(self):
        db = Database()
        db.name = self.config['name']
        self.db.query_drop(db)
        
        user = User()
        user.name = self.config['username']
        user.host = 'localhost'
        
        self.db.query_drop_user(user)
        self.config['created'] = False
        self.refresh()
