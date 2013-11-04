#!/bin/bash
rm dist/*
find -name '*.pyc' | xargs rm 
./deb.sh vh
./deb.sh vh-gunicorn
./deb.sh vh-mysql
./deb.sh vh-nginx
./deb.sh vh-php-fpm
./deb.sh vh-unicorn
./deb.sh vh-vsftpd
./deb.sh vh-puma
