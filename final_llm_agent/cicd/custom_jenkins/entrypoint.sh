#!/bin/bash
# This script is used as the entrypoint for the custom Jenkins Docker image.
# It sets the necessary permissions for Docker and then starts the Jenkins server.
chmod 777 /var/run/docker.sock
exec /usr/local/bin/jenkins.sh
