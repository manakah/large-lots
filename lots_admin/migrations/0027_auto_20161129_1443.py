# -*- coding: utf-8 -*-
# Generated by Django 1.10 on 2016-11-29 20:43
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('lots_admin', '0026_auto_20161129_0925'),
    ]

    operations = [
        migrations.AlterField(
            model_name='lot',
            name='planned_use',
            field=models.TextField(default=None, null=True),
        ),
    ]
