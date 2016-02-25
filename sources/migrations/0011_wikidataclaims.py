# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import core.utils.configuration
import json_field.fields


class Migration(migrations.Migration):

    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
        ('sources', '0010_auto_20160225_2307'),
    ]

    operations = [
        migrations.CreateModel(
            name='WikiDataClaims',
            fields=[
                ('id', models.AutoField(serialize=False, primary_key=True, verbose_name='ID', auto_created=True)),
                ('uri', models.CharField(db_index=True, default=None, max_length=255)),
                ('data_hash', models.CharField(db_index=True, default='', max_length=255)),
                ('config', core.utils.configuration.ConfigurationField()),
                ('request', json_field.fields.JSONField(default=None, help_text='Enter a valid JSON object')),
                ('head', json_field.fields.JSONField(default=None, help_text='Enter a valid JSON object')),
                ('body', models.TextField(default=None)),
                ('status', models.PositiveIntegerField(default=None)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
                ('purge_at', models.DateTimeField(null=True, blank=True)),
                ('retainer_id', models.PositiveIntegerField(null=True)),
                ('retainer_type', models.ForeignKey(to='contenttypes.ContentType', null=True)),
            ],
            options={
                'abstract': False,
            },
        ),
    ]
