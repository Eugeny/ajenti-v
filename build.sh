#!/bin/bash
rm dist/*
find -name '*.pyc' | xargs rm

./deb.sh vh
./deb.sh vh-gunicorn
./deb.sh vh-mysql
./deb.sh vh-nginx
./deb.sh vh-php-fpm
./deb.sh vh-php7.0-fpm
./deb.sh vh-php7.1-fpm
./deb.sh vh-php7.2-fpm
./deb.sh vh-php7.3-fpm
./deb.sh vh-unicorn
./deb.sh vh-vsftpd
./deb.sh vh-pureftpd
./deb.sh vh-puma
./deb.sh vh-nodejs
./deb.sh vh-mail

./rpm.sh vh
./rpm.sh vh-gunicorn
./rpm.sh vh-mysql
./rpm.sh vh-nginx
./rpm.sh vh-php-fpm
./rpm.sh vh-php7.0-fpm
./rpm.sh vh-php7.1-fpm
./rpm.sh vh-php7.2-fpm
./rpm.sh vh-php7.3-fpm
./rpm.sh vh-unicorn
./rpm.sh vh-vsftpd
./rpm.sh vh-pureftpd
./rpm.sh vh-puma
./rpm.sh vh-nodejs
./rpm.sh vh-mail

rm -r build
