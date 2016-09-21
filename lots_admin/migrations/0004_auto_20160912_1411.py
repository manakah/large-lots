# -*- coding: utf-8 -*-
# Generated by Django 1.10 on 2016-09-12 19:11
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('lots_admin', '0003_auto_20160912_1355'),
    ]

    operations = [
        migrations.CreateModel(
            name='ReviewStatus',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('denied', models.BooleanField(default=False)),
                ('email_sent', models.BooleanField()),
                ('denial_reason', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='lots_admin.DenialReason')),
                ('reviewer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.RemoveField(
            model_name='applicationstatus',
            name='denial_reason',
        ),
        migrations.RemoveField(
            model_name='applicationstatus',
            name='denied',
        ),
        migrations.RemoveField(
            model_name='applicationstatus',
            name='email_sent',
        ),
        migrations.RemoveField(
            model_name='applicationstatus',
            name='reviewer',
        ),
        migrations.AddField(
            model_name='applicationstatus',
            name='review_status',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='lots_admin.ReviewStatus'),
        ),
    ]