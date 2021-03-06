# -*- coding: utf-8 -*-
# Generated by Django 1.11.20 on 2019-04-02 09:54
from __future__ import unicode_literals

import datagrowth.configuration.fields
import datetime
from django.db import migrations, models
import django.db.models.deletion
import json_field.fields


class Migration(migrations.Migration):

    replaces = [('core', '0001_initial'), ('core', '0002_collective_individual'), ('core', '0003_growth'), ('core', '0004_communitymock'), ('core', '0005_auto_20150828_1659'), ('core', '0006_auto_20150828_1710'), ('core', '0007_auto_20150828_1806'), ('core', '0008_auto_20150828_1922'), ('core', '0009_auto_20150828_1945'), ('core', '0010_manifestation'), ('core', '0011_manifestation_config'), ('core', '0012_auto_20160219_1442'), ('core', '0013_auto_20160225_2307'), ('core', '0014_auto_20160226_1306'), ('core', '0015_auto_20160622_1528'), ('core', '0016_auto_20160627_2118'), ('core', '0017_auto_20170315_1639'), ('core', '0018_auto_20170910_1533'), ('core', '0019_auto_20171017_1444'), ('core', '0020_auto_20171119_1315'), ('core', '0021_manifestation_status'), ('core', '0022_auto_20180818_1827'), ('core', '0023_auto_20181202_1424'), ('core', '0024_auto_20190131_1706'), ('core', '0025_auto_20190402_0928'), ('core', '0026_auto_20190218_1423')]

    initial = True

    dependencies = [
        ('admin', '0002_logentry_remove_auto_add'),
        ('auth', '0006_require_contenttypes_0002'),
        ('contenttypes', '0002_remove_content_type_name'),
    ]

    operations = [
        migrations.CreateModel(
            name='HttpResourceMock',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('uri', models.CharField(db_index=True, default=None, max_length=255)),
                ('data_hash', models.CharField(db_index=True, default='', max_length=255)),
                ('config', datagrowth.configuration.fields.ConfigurationField()),
                ('request', json_field.fields.JSONField(default=None, help_text='Enter a valid JSON object')),
                ('head', json_field.fields.JSONField(default='{}', help_text='Enter a valid JSON object')),
                ('body', models.TextField(blank=True, default=None, null=True)),
                ('status', models.PositiveIntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
                ('purge_at', models.DateTimeField(blank=True, null=True)),
                ('retainer_id', models.PositiveIntegerField(blank=True, null=True)),
                ('retainer_type', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='contenttypes.ContentType')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Collective',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('community_type', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='+', to='contenttypes.ContentType')),
                ('community_id', models.PositiveIntegerField()),
                ('schema', json_field.fields.JSONField(default=None, help_text='Enter a valid JSON object')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Individual',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('community_type', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='+', to='contenttypes.ContentType')),
                ('community_id', models.PositiveIntegerField()),
                ('schema', json_field.fields.JSONField(default=None, help_text='Enter a valid JSON object')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
                ('properties', json_field.fields.JSONField(default={}, help_text='Enter a valid JSON object')),
                ('collective', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='core.Collective')),
                ('identity', models.CharField(blank=True, db_index=True, max_length=255, null=True)),
                ('reference', models.CharField(blank=True, db_index=True, max_length=255, null=True)),
            ],
            options={
                'get_latest_by': 'id',
                'ordering': ['id'],
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Growth',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('community_type', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='+', to='contenttypes.ContentType')),
                ('community_id', models.PositiveIntegerField()),
                ('type', models.CharField(max_length=255)),
                ('config', datagrowth.configuration.fields.ConfigurationField(default={})),
                ('process', models.CharField(choices=[('HttpResourceProcessor.fetch', 'Fetch content from HTTP resource'), ('HttpResourceProcessor.fetch_mass', 'Fetch content from multiple HTTP resources'), ('ExtractProcessor.extract_from_resource', 'Extract content from one or more resources')], max_length=255)),
                ('contribute', models.CharField(blank=True, choices=[('HttpResourceProcessor.fetch', 'Fetch content from HTTP resource'), ('HttpResourceProcessor.fetch_mass', 'Fetch content from multiple HTTP resources'), ('ExtractProcessor.extract_from_resource', 'Extract content from one or more resources')], max_length=255, null=True)),
                ('contribute_type', models.CharField(blank=True, choices=[('Append', 'Append')], max_length=255, null=True)),
                ('input_id', models.PositiveIntegerField(null=True)),
                ('output_id', models.PositiveIntegerField()),
                ('result_id', models.CharField(blank=True, max_length=255, null=True)),
                ('state', models.CharField(choices=[('Processing', 'Processing'), ('Partial', 'Partial'), ('Complete', 'Complete'), ('Contribute', 'Contribute'), ('Retry', 'Retry'), ('Error', 'Error'), ('New', 'New')], db_index=True, default='New', max_length=255)),
                ('is_finished', models.BooleanField(db_index=True, default=False)),
                ('input_type', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='+', to='contenttypes.ContentType')),
                ('output_type', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='+', to='contenttypes.ContentType')),
            ],
        ),
        migrations.CreateModel(
            name='CommunityMock',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('signature', models.CharField(db_index=True, max_length=255)),
                ('config', datagrowth.configuration.fields.ConfigurationField()),
                ('kernel_id', models.PositiveIntegerField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
                ('purge_at', models.DateTimeField(blank=True, null=True)),
                ('state', models.CharField(choices=[('Aborted', 'Aborted'), ('Asynchronous', 'Asynchronous'), ('New', 'New'), ('Ready', 'Ready'), ('Retry', 'Retry'), ('Synchronous', 'Synchronous')], default='New', max_length=255)),
                ('current_growth', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='core.Growth')),
                ('kernel_type', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='contenttypes.ContentType')),
            ],
            options={
                'abstract': False,
                'get_latest_by': 'created_at',
            },
        ),
        migrations.AlterField(
            model_name='collective',
            name='schema',
            field=json_field.fields.JSONField(default=None, help_text='Enter a valid JSON object'),
        ),
        migrations.AlterField(
            model_name='growth',
            name='input_id',
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='growth',
            name='input_type',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='+', to='contenttypes.ContentType'),
        ),
        migrations.AlterField(
            model_name='growth',
            name='output_id',
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='growth',
            name='output_type',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='+', to='contenttypes.ContentType'),
        ),
        migrations.AddField(
            model_name='collective',
            name='indexes',
            field=json_field.fields.JSONField(blank=True, default={}, help_text='Enter a valid JSON object', null=True),
        ),
        migrations.AddField(
            model_name='collective',
            name='identifier',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.CreateModel(
            name='Manifestation',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('community_id', models.PositiveIntegerField()),
                ('uri', models.CharField(db_index=True, default=None, max_length=255)),
                ('data', json_field.fields.JSONField(default='null', help_text='Enter a valid JSON object', null=True)),
                ('task', models.CharField(blank=True, max_length=255, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
                ('community_type', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='+', to='contenttypes.ContentType')),
                ('config', datagrowth.configuration.fields.ConfigurationField()),
                ('modified_at', models.DateTimeField(auto_now=True)),
                ('purge_at', models.DateTimeField(blank=True, null=True)),
                ('retainer_id', models.PositiveIntegerField(blank=True, null=True)),
                ('retainer_type', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='contenttypes.ContentType')),
                ('status', models.PositiveIntegerField(default=0)),
            ],
            options={
                'get_latest_by': 'id',
                'ordering': ('id',),
            },
        ),
        migrations.AlterField(
            model_name='growth',
            name='config',
            field=datagrowth.configuration.fields.ConfigurationField(),
        ),
        migrations.AlterField(
            model_name='growth',
            name='state',
            field=models.CharField(choices=[('Complete', 'Complete'), ('Contribute', 'Contribute'), ('Error', 'Error'), ('New', 'New'), ('Partial', 'Partial'), ('Processing', 'Processing'), ('Retry', 'Retry')], db_index=True, default='New', max_length=255),
        ),
        migrations.AlterField(
            model_name='growth',
            name='contribute_type',
            field=models.CharField(blank=True, choices=[('Append', 'Append'), ('Inline', 'Inline')], max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name='growth',
            name='contribute',
            field=models.CharField(blank=True, choices=[('HttpResourceProcessor.fetch', 'Fetch content from HTTP resource'), ('HttpResourceProcessor.fetch_mass', 'Fetch content from multiple HTTP resources'), ('ExtractProcessor.extract_from_resource', 'Extract content from one or more resources'), ('ExtractProcessor.pass_resource_through', "Take content 'as is' from one or more resources")], max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name='growth',
            name='contribute_type',
            field=models.CharField(blank=True, choices=[('Append', 'Append'), ('Inline', 'Inline'), ('Update', 'Update')], max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name='growth',
            name='process',
            field=models.CharField(choices=[('HttpResourceProcessor.fetch', 'Fetch content from HTTP resource'), ('HttpResourceProcessor.fetch_mass', 'Fetch content from multiple HTTP resources'), ('ExtractProcessor.extract_from_resource', 'Extract content from one or more resources'), ('ExtractProcessor.pass_resource_through', "Take content 'as is' from one or more resources")], max_length=255),
        ),
        migrations.AlterModelOptions(
            name='collective',
            options={'get_latest_by': 'created_at', 'ordering': ['created_at']},
        ),
        migrations.RemoveField(
            model_name='collective',
            name='indexes',
        ),
        migrations.AlterModelOptions(
            name='collective',
            options={'get_latest_by': 'id', 'ordering': ['id']},
        ),
        migrations.AlterModelOptions(
            name='growth',
            options={'get_latest_by': 'id', 'ordering': ('id',)},
        ),
        migrations.AddField(
            model_name='collective',
            name='name',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='collective',
            name='referee',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
    ]
