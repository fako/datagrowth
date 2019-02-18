# -*- coding: utf-8 -*-
# Generated by Django 1.11.15 on 2019-02-18 11:56
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0024_auto_20190131_1706'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='growth',
            options={'get_latest_by': 'id', 'ordering': ('id',)},
        ),
        migrations.AlterModelOptions(
            name='individual',
            options={'get_latest_by': 'id', 'ordering': ['id']},
        ),
        migrations.AlterModelOptions(
            name='manifestation',
            options={'get_latest_by': 'id', 'ordering': ('id',)},
        ),
    ]
