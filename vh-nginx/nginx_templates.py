import multiprocessing


TEMPLATE_CONFIG_FILE = """
#AUTOMATICALLY GENERATED - DO NO EDIT!

user %(user)s %(user)s;
pid /var/run/nginx.pid;
worker_processes %(workers)s;
worker_rlimit_nofile 100000;

events {
    worker_connections  4096;
    multi_accept on;
}

http {
    default_type application/octet-stream;

    access_log off;
    error_log  %(log_root)s/error.log crit;

    sendfile on;
    tcp_nopush on;

    keepalive_timeout 20;
    client_header_timeout 20;
    client_body_timeout 20;
    reset_timedout_connection on;
    send_timeout 20;

    types_hash_max_size 2048;

    gzip on;
    gzip_disable "msie6";
    gzip_proxied any;
    gzip_min_length 256;
    gzip_comp_level 4;
    gzip_types text/plain text/css application/json application/x-javascript text/xml application/xml application/xml+rss text/javascript application/javascript text/x-js;

    server_names_hash_bucket_size 128;

    include mime.conf;
    charset UTF-8;

    open_file_cache max=100000 inactive=20s;
    open_file_cache_valid 30s;
    open_file_cache_min_uses 2;
    open_file_cache_errors on;

    server_tokens off;

    include proxy.conf;
    include fcgi.conf;

    include conf.d/*.conf;
    include /etc/nginx.custom.d/*.conf;
}
""" % {
    'workers': multiprocessing.cpu_count(),
    'log_root': '/var/log/nginx',
    'user': 'www-data',
}

TEMPLATE_CONFIG_PROXY = """
proxy_redirect          off;
proxy_set_header        Host            $host;
proxy_set_header        X-Real-IP       $remote_addr;
proxy_set_header        X-Forwarded-For $proxy_add_x_forwarded_for;
client_max_body_size    10m;
client_body_buffer_size 128k;
proxy_connect_timeout   90;
proxy_send_timeout      90;
proxy_read_timeout      90;
proxy_buffers           32 4k;
"""

TEMPLATE_CONFIG_FCGI = """
fastcgi_param   QUERY_STRING            $query_string;
fastcgi_param   REQUEST_METHOD          $request_method;
fastcgi_param   CONTENT_TYPE            $content_type;
fastcgi_param   CONTENT_LENGTH          $content_length;

fastcgi_param   SCRIPT_FILENAME         $document_root$fastcgi_script_name;
fastcgi_param   SCRIPT_NAME             $fastcgi_script_name;
fastcgi_param   PATH_INFO               $fastcgi_path_info;
fastcgi_param   REQUEST_URI             $request_uri;
fastcgi_param   DOCUMENT_URI            $document_uri;
fastcgi_param   DOCUMENT_ROOT           $document_root;
fastcgi_param   SERVER_PROTOCOL         $server_protocol;

fastcgi_param   GATEWAY_INTERFACE       CGI/1.1;
fastcgi_param   SERVER_SOFTWARE         nginx/$nginx_version;

fastcgi_param   REMOTE_ADDR             $remote_addr;
fastcgi_param   REMOTE_PORT             $remote_port;
fastcgi_param   SERVER_ADDR             $server_addr;
fastcgi_param   SERVER_PORT             $server_port;
fastcgi_param   SERVER_NAME             $server_name;

fastcgi_param   HTTPS                   $https;

fastcgi_param   REDIRECT_STATUS         200;
"""

TEMPLATE_CONFIG_MIME = """
types {
    text/html                             html htm shtml;
    text/css                              css;
    text/xml                              xml rss;
    image/gif                             gif;
    image/jpeg                            jpeg jpg;
    application/x-javascript              js;
    text/plain                            txt;
    text/x-component                      htc;
    text/mathml                           mml;
    image/png                             png;
    image/svg+xml                         svg svgz;
    image/x-icon                          ico;
    image/x-jng                           jng;
    image/vnd.wap.wbmp                    wbmp;
    application/java-archive              jar war ear;
    application/mac-binhex40              hqx;
    application/pdf                       pdf;
    application/x-cocoa                   cco;
    application/x-java-archive-diff       jardiff;
    application/x-java-jnlp-file          jnlp;
    application/x-makeself                run;
    application/x-perl                    pl pm;
    application/x-pilot                   prc pdb;
    application/x-rar-compressed          rar;
    application/x-redhat-package-manager  rpm;
    application/x-sea                     sea;
    application/x-shockwave-flash         swf;
    application/x-stuffit                 sit;
    application/x-tcl                     tcl tk;
    application/x-x509-ca-cert            der pem crt;
    application/x-xpinstall               xpi;
    application/zip                       zip;
    application/octet-stream              deb;
    application/octet-stream              bin exe dll;
    application/octet-stream              dmg;
    application/octet-stream              eot;
    application/octet-stream              iso img;
    application/octet-stream              msi msp msm;
    audio/mpeg                            mp3;
    audio/x-realaudio                     ra;
    video/mpeg                            mpeg mpg;
    video/quicktime                       mov;
    video/x-flv                           flv;
    video/x-msvideo                       avi;
    video/x-ms-wmv                        wmv;
    video/x-ms-asf                        asx asf;
    video/x-mng                           mng;
}
"""

TEMPLATE_WEBSITE = """
#AUTOMATICALLY GENERATED - DO NO EDIT!

server {
    %(ports)s
    %(ssl_cert)s
    %(ssl_key)s
    %(server_name)s

    access_log /var/log/nginx/%(slug)s.access.log;
    error_log /var/log/nginx/%(slug)s.error.log;

    root %(root)s;
    index index.html index.htm index.php;

    %(custom_conf)s

    %(maintenance)s
    %(locations)s
}
"""

TEMPLATE_MAINTENANCE = """
    location / {
        return 503;
        error_page 503 @maintenance;
    }

    location @maintenance {
        root /var/lib/ajenti/plugins/vh/extras;
        rewrite ^(.*)$ /maintenance.html break;
    }
"""

TEMPLATE_LOCATION = """
    location %(match)s %(pattern)s {
        %(path)s
        %(custom_conf)s
        %(content)s
    }
"""

TEMPLATE_LOCATION_CONTENT_STATIC = """
        %(autoindex)s
"""

TEMPLATE_LOCATION_CONTENT_PROXY = """
        proxy_pass %(url)s;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header HTTPS   $https;
"""

TEMPLATE_LOCATION_CONTENT_FCGI = """
        include fcgi.conf;
        fastcgi_pass %(url)s;
"""

TEMPLATE_LOCATION_CONTENT_PHP_FCGI = """
        fastcgi_index index.php;
        include fcgi.conf;
        fastcgi_pass unix:/var/run/php-fcgi-%(id)s.sock;
        fastcgi_param SCRIPT_FILENAME $document_root$fastcgi_script_name;
"""

TEMPLATE_LOCATION_CONTENT_PYTHON_WSGI = """
        proxy_pass http://unix:/var/run/gunicorn-%(id)s.sock;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
"""

TEMPLATE_LOCATION_CONTENT_RUBY_UNICORN = """
        proxy_pass http://unix:/var/run/unicorn-%(id)s.sock;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
"""

TEMPLATE_LOCATION_CONTENT_RUBY_PUMA = """
        proxy_pass http://unix:/var/run/puma-%(id)s.sock;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
"""


TEMPLATE_LOCATION_CONTENT_NODEJS = """
        proxy_pass http://127.0.0.1:%(port)i;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
"""
