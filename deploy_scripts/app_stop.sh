#!/bin/bash

supervisorctl stop large-lots:\'large-lots\'
supervisorctl start large-lots-maintenance
