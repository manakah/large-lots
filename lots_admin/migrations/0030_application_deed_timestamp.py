# -*- coding: utf-8 -*-
# Generated by Django 1.10 on 2017-02-03 19:11
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('lots_admin', '0029_address_community'),
    ]

    operations = [
        migrations.AddField(
            model_name='application',
            name='deed_timestamp',
            field=models.DateTimeField(null=True),
        ),
    ]