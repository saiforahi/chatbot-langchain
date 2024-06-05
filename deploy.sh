#!/bin/bash
# Deployment script deploy.sh

# Navigate to the project directory
cd /home/ubuntu/genai_flask_app

# Pull the latest changes
git fetch --all
git reset --hard origin/dev

# Optionally, run other commands, like installing dependencies
# pip install -r requirements.txt

# Restart Nginx to apply changes
sudo systemctl restart nginx
