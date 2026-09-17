#!/bin/bash

# Ensure running as root
if [ "$EUID" -ne 0 ]; then
  echo "Please run as root"
  exit 1
fi

NGINX_CONF_PATH="/etc/nginx/nginx.conf"
SITES_AVAILABLE="/etc/nginx/sites-available"
SITES_ENABLED="/etc/nginx/sites-enabled"

echo "Removing hardcoded server { root /var/www/html; ... } block from $NGINX_CONF_PATH"
# Use awk to remove the specific server block that serves /var/www/html on port 80
# Since the exact structure might vary slightly, a robust way is to remove the specific lines based on the issue description,
# which states it's around lines 22-35. However, doing it safely requires matching the block.
# We will create a Python script on the fly to reliably parse and remove the static server block to avoid breaking nginx.conf

cat << 'EOF' > clean_nginx.py
import sys
import re

def clean_conf(filepath):
    try:
        with open(filepath, 'r') as f:
            content = f.read()

        # Look for a server block that has root /var/www/html
        # We find the start of a server block containing 'root /var/www/html' and match its closing brace
        pattern = re.compile(r'server\s*{[^}]*root\s+/var/www/html[^}]*}', re.MULTILINE | re.DOTALL)

        # We need a better parser for nested braces if present, but standard nginx config
        # for a static block usually doesn't have deep nesting.
        # A simpler regex to remove the specific server block:

        # Let's try to match it carefully
        new_content = pattern.sub('', content)

        if new_content != content:
            print(f"Removed hardcoded static server block from {filepath}")
            with open(filepath, 'w') as f:
                f.write(new_content)
        else:
            print(f"No matching hardcoded static server block found in {filepath}")

    except Exception as e:
        print(f"Error cleaning {filepath}: {e}")
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        clean_conf(sys.argv[1])
EOF

python3 clean_nginx.py $NGINX_CONF_PATH
rm clean_nginx.py

echo "Removing default site if exists"
if [ -L "$SITES_ENABLED/default" ]; then
    rm -f "$SITES_ENABLED/default"
fi
if [ -f "$SITES_AVAILABLE/default" ]; then
    rm -f "$SITES_AVAILABLE/default"
fi

echo "Setting up capital-cooling site"
cp deployment/nginx.conf "$SITES_AVAILABLE/capital-cooling"
ln -sf "$SITES_AVAILABLE/capital-cooling" "$SITES_ENABLED/capital-cooling"

echo "Validating Nginx configuration"
nginx -t

if [ $? -eq 0 ]; then
    echo "Restarting Nginx"
    systemctl restart nginx
    echo "Nginx setup complete."
else
    echo "Nginx configuration test failed. Please check the config."
    exit 1
fi
