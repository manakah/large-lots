# -*- coding: utf-8 -*-
# Generated by Django 1.10 on 2016-09-27 15:53
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('lots_admin', '0022_auto_20160927_1051'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='address',
            name='latitude',
        ),
        migrations.RemoveField(
            model_name='address',
            name='longitude',
        ),
    ]
