# -*- coding: utf-8 -*-
# Generated by Django 1.10 on 2018-01-30 20:07
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('lots_admin', '0035_application_closing_invite_sent'),
    ]

    operations = [
        migrations.AddField(
            model_name='application',
            name='organization_confirmed',
            field=models.BooleanField(default=False),
        ),
    ]
