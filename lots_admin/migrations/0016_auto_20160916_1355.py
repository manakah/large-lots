# -*- coding: utf-8 -*-
# Generated by Django 1.10 on 2016-09-16 18:55
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('lots_admin', '0015_auto_20160916_1341'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='reviewstatus',
            name='denied',
        ),
        migrations.AddField(
            model_name='application',
            name='denied',
            field=models.BooleanField(default=False),
        ),
    ]
