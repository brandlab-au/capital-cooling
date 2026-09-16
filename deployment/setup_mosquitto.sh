#!/bin/bash
# Run this script with sudo to install and configure Mosquitto MQTT broker

echo "Installing Mosquitto..."
apt-get update
apt-get install -y mosquitto mosquitto-clients

echo "Setting up basic authentication..."
# Create a password file and prompt for a password for the user 'mqtt_user'
mosquitto_passwd -c /etc/mosquitto/passwd mqtt_user

echo "Configuring Mosquitto..."
cat << 'CONF' > /etc/mosquitto/conf.d/default.conf
allow_anonymous false
password_file /etc/mosquitto/passwd
listener 1883
CONF

echo "Restarting Mosquitto..."
systemctl restart mosquitto
systemctl enable mosquitto

echo "Mosquitto installation and configuration complete!"
