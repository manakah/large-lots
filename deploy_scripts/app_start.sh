#!/bin/bash

supervisorctl stop large-lots-maintenance
supervisorctl start large-lots:\'large-lots\'
