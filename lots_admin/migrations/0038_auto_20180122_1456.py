# -*- coding: utf-8 -*-
# Generated by Django 1.10 on 2018-01-22 20:56
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('lots_admin', '0037_auto_20180118_1550'),
    ]

    operations = [
        migrations.AddField(
            model_name='principalprofile',
            name='drivers_license_state',
            field=models.CharField(default='IL', max_length=2),
        ),
        migrations.AddField(
            model_name='principalprofile',
            name='license_plate_state',
            field=models.CharField(default='IL', max_length=2),
        ),
    ]
