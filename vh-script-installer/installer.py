import uuid
import urllib2
import tarfile
import shutil
import os

from contextlib import closing

from ajenti.api import *
from ajenti.ui import on
from ajenti.ui.binder import Binder

from ajenti.plugins.mysql.api import MySQLDB
from ajenti.plugins.db_common.api import Database, User
from ajenti.plugins.vh.extensions import BaseExtension


@plugin
class ScriptInstaller (BaseExtension):
    default_config = {
        'databases': [],
        'users': [],
    }
    name = 'Script Installer'

    def init(self):
        self.append(self.ui.inflate('vh-script-installer:main'))
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

        self.binder.setup().populate()
        self.find('wp-path').value = self.website.root
        self.find('wp-db-name').value = self.website.slug+'_wp'
        self.find('wp-db-user').value = self.website.slug+'_wp'
        
        self.find('wp-db-pass').value = str(uuid.uuid4())

        self.find('wp-db-name').delete_item = lambda i, c: self.on_delete_db(i)
        self.find('wp-db-user').delete_item = lambda i, c: self.on_delete_user(i)
        
    def update(self):
        self.binder.update()

    def on_destroy(self):
        pass

    @on('wp-install', 'click')
    def on_install_wp(self):
        
        # Define User, Pass and DB Name
        db_user = self.find('wp-db-user').value
        db_pass = self.find('wp-db-pass').value
        db_name = self.find('wp-db-name').value
        
        # Download Latest Wordpress
        url = 'http://wordpress.org/latest.tar.gz'
        tmpfile = '/tmp/wp.tar.gz'
        
        with open(tmpfile,'wb') as f:
            f.write(urllib2.urlopen('http://wordpress.org/latest.tar.gz').read())
            f.close()
            
        with closing(tarfile.open('/tmp/wp.tar.gz','r')) as tar:
            tar.extractall(path="/tmp/wp")
            
        for f in os.listdir('/tmp/wp/wordpress/'):
            src = '/tmp/wp/wordpress/'+f
            dst = self.website.root+'/'+f
            shutil.move(src,dst)
        
        if os.path.isfile(tmpfile):
            os.remove(tmpfile)
        
        if os.path.exists("/tmp/wp"):
            shutil.rmtree("/tmp/wp")
            
        self.context.notify('info', _('Wordpress Downloaded !'))
        
        # Generate Databases
        self.generate_db(db_name,db_user,db_pass)
        
        # Configure Wordpress
        config_string = ""
        if os.path.isfile(self.website.root+'/wp-config-sample.php'):
            
            if not os.path.isfile(self.website.root+'/wp-config.php'):
                
                salt = urllib2.urlopen('https://api.wordpress.org/secret-key/1.1/salt/').read()
                
                with open (self.website.root+'/wp-config-sample.php','r') as sample_file:
                    config_string = sample_file.read()
                    config_string = config_string.replace("""define('AUTH_KEY',         'put your unique phrase here');
define('SECURE_AUTH_KEY',  'put your unique phrase here');
define('LOGGED_IN_KEY',    'put your unique phrase here');
define('NONCE_KEY',        'put your unique phrase here');
define('AUTH_SALT',        'put your unique phrase here');
define('SECURE_AUTH_SALT', 'put your unique phrase here');
define('LOGGED_IN_SALT',   'put your unique phrase here');
define('NONCE_SALT',       'put your unique phrase here');""",salt)
                    config_string = config_string.replace('database_name_here',db_name)
                    config_string = config_string.replace('username_here',db_user)
                    config_string = config_string.replace('password_here',db_pass)
                    sample_file.close()
                    
                with open(self.website.root+'/wp-config.php','wb') as wp_config:
                    wp_config.write(config_string) 
                    wp_config.close()   
                    
            else:
                self.context.notify('error', _('Config file already exists!'))
                return
                
        else:
            self.context.notify('error', _('File wp-config-sample.php\nNot Found!'))
            return
            
        
        self.context.notify('info', _('Wordpress Installed !'))
        self.refresh()
        self.try_save()
    
    def generate_db(self,db_name,db_user,db_pass):
        
        # Create Database
        try:
            self.db.query_databases()
        except Exception, e:
            self.context.notify('error', str(e))
            self.context.launch('configure-plugin', plugin=self.db)
            return
            
        dbname = db_name

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

        # Create User
        username = db_user
        password = db_pass
        
        for user in self.db.query_users():
            if user.name == username:
                self.context.notify('error', _('This username is already exists'))
                return

        user_cfg = {
            'name': username,
            'password': password,
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
        
        # Grant User
        dbku = Database()
        dbku.name = dbname
        self.db.query_grant(user, dbku)
        
        self.context.notify('info', _('Database Created !'))
        
        self.refresh()
        self.try_save()

    def try_save(self):
        if self.editor_ui is not None:
            self.editor_ui.save_data()
