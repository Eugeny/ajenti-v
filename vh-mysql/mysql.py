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
        #'created': False,
        #'name': None,
        #'user': None,
        #'password': None,
        'databases': [],
        'users': [],
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
        if not 'databases' in self.config:
            if self.config['created']:
                self.config['databases'] = [{
                    'name': self.config['name'],
                }]
                self.config['users'] = [{
                    'name': self.config['user'],
                    'password': self.config['password'],
                }]
            else:
                self.config['databases'] = []
                self.config['users'] = []

            del self.config['created']
            del self.config['name']
            del self.config['user']
            del self.config['password']

        def post_db_bind(object, collection, item, ui):
            ui.find('detach').on('click', self.on_detach_db, item)

        self.find('databases').post_item_bind = post_db_bind

        def post_user_bind(object, collection, item, ui):
            ui.find('detach').on('click', self.on_detach_user, item)

        self.find('users').post_item_bind = post_user_bind

        self.binder.setup().populate()
        self.find('db-name').value = self.website.slug
        self.find('db-username').value = self.website.slug

        self.find('databases').delete_item = lambda i, c: self.on_delete_db(i)
        self.find('users').delete_item = lambda i, c: self.on_delete_user(i)
        
    def update(self):
        self.binder.update()

    def on_destroy(self):
        pass

    @on('create-db', 'click')
    def on_create_db(self):
        try:
            self.db.query_databases()
        except Exception, e:
            self.context.notify('error', str(e))
            self.context.launch('configure-plugin', plugin=self.db)
            return

        dbname = self.find('db-name').value

        for db in self.db.query_databases():
            if db.name == dbname:
                self.context.notify('error', _('This database name is already used'))
                return
        
        db_cfg = {'name': dbname}

        try:
            self.db.query_create(db_cfg['name'])
        except Exception, e:
            self.context.notify('error', str(e))
            return

        self.config['databases'].append(db_cfg)

        self.on_grant()
        self.refresh()
        self.try_save()

    @on('create-user', 'click')
    def on_create_user(self):
        try:
            self.db.query_databases()
        except Exception, e:
            self.context.notify('error', str(e))
            self.context.launch('configure-plugin', plugin=self.db)
            return

        username = self.find('db-username').value
        for user in self.db.query_users():
            if user.name == username:
                self.context.notify('error', _('This username is already used'))
                return

        user_cfg = {
            'name': username,
            'password': str(uuid.uuid4()),
        }

        user = User()
        user.name = user_cfg['name']
        user.password = user_cfg['password']
        user.host = '%'
        try:
            self.db.query_create_user(user)
        except Exception, e:
            self.context.notify('error', str(e))
            return

        self.config['users'].append(user_cfg)

        self.on_grant()
        self.refresh()
        self.try_save()
    
    @on('grant', 'click')
    def on_grant(self):
        for db_cfg in self.config['databases']:
            db = Database()
            db.name = db_cfg['name']
            for user_cfg in self.config['users']:
                user = User()
                user.name = user_cfg['name']
                user.password = user_cfg['password']
                user.host = '%'
                self.db.query_grant(user, db)
        self.context.notify('info', _('Permissions granted.'))

    def on_delete_db(self, db_cfg):
        db = Database()
        db.name = db_cfg['name']
        try:
            self.db.query_drop(db)
        except Exception, e:
            # I'm gonna burn in hell for this...
            if not 'ERROR 1008' in e:
                self.context.notify('error', str(e))
                return

        self.config['databases'].remove(db)
        self.refresh()
        self.try_save()
        
    def on_delete_user(self, user_cfg):
        user = User()
        user.name = user_cfg['name']
        user.host = '%'
        
        try:
            self.db.query_drop_user(user)
        except Exception, e:
            if not 'ERROR 1008' in e:
                self.context.notify('error', str(e))
                return

        self.config['users'].remove(user_cfg)
        self.refresh()
        self.try_save()

    def on_detach_db(self, db_cfg):
        self.config['databases'].remove(db_cfg)
        self.refresh()
        self.try_save()

    def on_detach_user(self, user_cfg):
        self.config['users'].remove(user_cfg)
        self.refresh()
        self.try_save()

    def try_save(self):
        if self.editor_ui is not None:
            self.editor_ui.save_data()
