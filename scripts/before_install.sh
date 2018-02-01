#!/bin/bash
set -euo pipefail

# Make directory for project
mkdir -p /home/datamade/large-lots-modern-deployment

# Decrypt files and move them to the right location
cd /opt/codedeploy-agent/deployment-root/$DEPLOYMENT_GROUP_ID/$DEPLOYMENT_ID/deployment-archive/ && chown -R datamade.datamade . && sudo -H -u datamade blackbox_postdeploy

