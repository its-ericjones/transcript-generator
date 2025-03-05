#!/bin/bash

echo "------------------------"
echo "REMOVING LAMP COMPONENTS"
echo "------------------------"
sleep 1

echo "--------------------"
echo "STOPPING SERVICES..."
echo "--------------------"
sleep 1
sudo systemctl stop apache2
sudo systemctl stop mariadb

echo "---------------------"
echo "DISABLING SERVICES..."
echo "---------------------"
sleep 1
sudo systemctl disable apache2
sudo systemctl disable mariadb

echo "----------------------"
echo "UNINSTALLING APACHE..."
echo "----------------------"
sleep 1
sudo apt-get remove --purge apache2 -y
sudo apt-get autoremove -y
sudo apt-get clean

echo "-------------------"
echo "UNINSTALLING PHP..."
echo "-------------------"
sleep 1
sudo apt-get remove --purge php libapache2-mod-php -y
sudo apt-get autoremove -y
sudo apt-get clean

echo "-----------------------"
echo "UNINSTALLING MARIADB..."
echo "-----------------------"
sleep 1
sudo apt-get remove --purge mariadb-server -y
sudo apt-get autoremove -y
sudo apt-get clean

echo "----------------------------------------"
echo "REMOVING CONFIGURATION AND DATA FILES..."
echo "----------------------------------------"
sleep 1
sudo rm -rf /etc/apache2 /var/www/html
sudo rm -rf /etc/php /var/lib/php
sudo rm -rf /etc/mysql /var/lib/mysql
sudo rm -rf /var/log/apache2 /var/log/mysql

echo "----------------------"
echo "LAMP REMOVAL COMPLETE"
echo "----------------------"