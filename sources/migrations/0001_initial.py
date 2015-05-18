# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import jsonfield.fields
import core.utils.configuration
import core.models.organisms.protocols


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='HttpResourceMock',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('uri', models.CharField(default=None, max_length=255, db_index=True)),
                ('post_data', models.CharField(default=b'', max_length=255, db_index=True)),
                ('request', jsonfield.fields.JSONField(default=None)),
                ('head', jsonfield.fields.JSONField(default=None)),
                ('body', models.TextField(default=None)),
                ('status', models.PositiveIntegerField(default=None)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
                ('purge_at', models.DateTimeField(null=True, blank=True)),
                ('config', core.utils.configuration.ConfigurationField(default={})),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model, core.models.organisms.protocols.OrganismInputProtocol),
        ),
    ]
