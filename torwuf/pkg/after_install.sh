#!/bin/sh -e

adduser --system --group www-torwuf
sudo -u www-torwuf mkdir -p /home/www-torwuf/torwuf-service/
sudo chmod g+rwxs /home/www-torwuf/torwuf-service/
sudo -u www-torwuf mkdir -p /home/www-torwuf/torwuf-service/www/
sudo -u www-torwuf touch /home/www-torwuf/torwuf-service/www/dummy.fcgi
sudo -u www-torwuf mkdir -p /home/www-torwuf/torwuf-service/www/z/
sudo -u www-torwuf ln -f -s /opt/torwuf/share/www/favicon.ico /home/www-torwuf/torwuf-service/www/favicon.ico
chmod +x /opt/torwuf/sbin/*
chmod 644 /etc/cron.d/torwuf-service

start torwuf-service
echo "after_install script done"

