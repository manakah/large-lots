# -*- coding: utf-8 -*-
# Generated by Django 1.10 on 2017-01-18 17:50
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('lots_admin', '0028_auto_20161130_0908'),
    ]

    operations = [
        migrations.AddField(
            model_name='address',
            name='community',
            field=models.CharField(max_length=255, null=True),
        ),
    ]
