# -*- coding: utf-8 -*-
# Generated by Django 1.10 on 2017-06-30 20:13
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('lots_admin', '0031_applicationstatus_lottery'),
    ]

    operations = [
        migrations.AddField(
            model_name='applicationstatus',
            name='eds_sent',
            field=models.BooleanField(default=False),
        ),
    ]
