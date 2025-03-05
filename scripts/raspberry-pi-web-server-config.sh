#!/bin/bash

echo "--------------------"
echo "UPDATING PACKAGES..."
echo "--------------------"
sleep 1
sudo apt-get update

echo "--------------------------------"
echo "PACKAGES INSTALLED SUCCESSFULLY!"
echo "--------------------------------"
sleep 1

echo "---------------------"
echo "INSTALLING APACHE2..."
echo "---------------------"
sleep 1
sudo apt-get install apache2 -y

echo "-------------------------------"
echo "APACHE2 INSTALLED SUCCESSFULLY!"
echo "-------------------------------"
sleep 1

echo "-----------------"
echo "INSTALLING PHP..."
echo "-----------------"
sleep 1
sudo apt-get install php libapache2-mod-php -y

echo "---------------------------"
echo "PHP INSTALLED SUCCESSFULLY!"
echo "---------------------------"
sleep 1

echo "---------------------"
echo "INSTALLING MARIADB..."
echo "---------------------"
sleep 1
sudo apt-get install mariadb-server
sudo mysql_secure_installation

echo "-------------------------------"
echo "MARIADB INSTALLED SUCCESSFULLY!"
echo "-------------------------------"
sleep 1

echo "---------------------------------"
echo "INSTALLING PHP-MYSQL CONNECTOR..."
echo "---------------------------------"
sleep 1
sudo apt install php-mysql

echo "---------------------------------"
echo "PHP-MYSQL INSTALLED SUCCESSFULLY!"
echo "---------------------------------"
sleep 1
echo "----------------------------"
echo "RESTARTING APACH2 SERVICE..."
echo "----------------------------"
sleep 1
sudo service apache2 restart

echo "---------------------------------------------------------------------------------------------"
echo "WEB SERVER INSTALLED SUCCESSFULLY! VISIT HOST.LOCAL IN A WEB BROWSER TO VIEW THE TEST PAGE..."
echo "---------------------------------------------------------------------------------------------"