# -*- coding: utf-8 -*-
# Generated by Django 1.11.15 on 2019-01-31 17:06
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0023_auto_20181202_1424'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='collective',
            name='indexes',
        ),
        migrations.RemoveField(
            model_name='individual',
            name='index',
        ),
    ]
