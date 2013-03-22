#!/bin/sh -e

adduser --system --group www-torwuf
sudo -u www-torwuf mkdir -p /home/www-torwuf/torwuf-service/
sudo chmod g+rwxs /home/www-torwuf/torwuf-service/
sudo -u www-torwuf mkdir -p /home/www-torwuf/torwuf-service/www/
sudo -u www-torwuf touch /home/www-torwuf/torwuf-service/www/dummy.fcgi
sudo -u www-torwuf mkdir -p /home/www-torwuf/torwuf-service/www/z/
sudo -u www-torwuf ln -f -s /usr/local/torwuf/share/www/favicon.ico /home/www-torwuf/torwuf-service/www/favicon.ico
chmod +x /usr/local/torwuf/sbin/*

python3 /usr/local/torwuf/share/virtualenv.py /usr/local/torwuf/
/usr/local/torwuf/bin/python3 -m pip install /usr/local/torwuf/share/torwuf_dependencies.pybundle

start torwuf-service
echo "after_install script done"

