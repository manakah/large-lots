#!/bin/bash

# Generate new map data
make -C data/pilot_5 all

# TODO: Upload to CartoDB (need to figure out how to get API keys without
# putting in version control)

chown -R datamade.www-data /home/datamade
/home/datamade/.virtualenvs/dedupe-api/bin/pip install -r /home/datamade/large-lots/requirements.txt --upgrade

# Copy config file from S3
aws s3 cp s3://datamade-codedeploy/configs/largelots_config.py /home/datamade/large-lots/lots/local_settings.py --region us-east-1
chown datamade.www-data /home/datamade/large-lots/lots/local_settings.py

# Run migrations
/home/datamade/.virtualenvs/dedupe-api/bin/python /home/datamade/large-lots/manage.py migrate 
