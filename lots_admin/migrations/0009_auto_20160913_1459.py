# -*- coding: utf-8 -*-
# Generated by Django 1.10 on 2016-09-13 19:59
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('lots_admin', '0008_auto_20160913_0931'),
    ]

    operations = [
        migrations.AlterField(
            model_name='application',
            name='status',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='lots_admin.ApplicationStatus'),
        ),
    ]
