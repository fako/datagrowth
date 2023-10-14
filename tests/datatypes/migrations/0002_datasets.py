# Generated by Django 3.2.16 on 2023-10-13 13:08

import datagrowth.configuration.fields
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
        ('datatypes', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Batch',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('processor', models.CharField(max_length=256)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Dataset',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('signature', models.CharField(db_index=True, max_length=255)),
                ('config', datagrowth.configuration.fields.ConfigurationField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='DatasetMock',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('signature', models.CharField(db_index=True, max_length=255)),
                ('config', datagrowth.configuration.fields.ConfigurationField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.AddField(
            model_name='collection',
            name='derivatives',
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name='collection',
            name='finished_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='collection',
            name='pending_at',
            field=models.DateTimeField(blank=True, default=django.utils.timezone.now, null=True),
        ),
        migrations.AddField(
            model_name='collection',
            name='task_results',
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name='collection',
            name='tasks',
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name='document',
            name='derivatives',
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name='document',
            name='finished_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='document',
            name='pending_at',
            field=models.DateTimeField(blank=True, default=django.utils.timezone.now, null=True),
        ),
        migrations.AddField(
            model_name='document',
            name='task_results',
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name='document',
            name='tasks',
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AlterField(
            model_name='document',
            name='properties',
            field=models.JSONField(default=dict),
        ),
        migrations.CreateModel(
            name='ProcessResult',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('result_id', models.PositiveIntegerField(blank=True, null=True)),
                ('batch', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='datatypes.batch')),
                ('document', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='datatypes.document')),
                ('result_type', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='+', to='contenttypes.contenttype')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='DatasetVersion',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tasks', models.JSONField(blank=True, default=dict)),
                ('task_results', models.JSONField(blank=True, default=dict)),
                ('derivatives', models.JSONField(blank=True, default=dict)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
                ('pending_at', models.DateTimeField(blank=True, default=django.utils.timezone.now, null=True)),
                ('finished_at', models.DateTimeField(blank=True, null=True)),
                ('dataset_id', models.PositiveIntegerField()),
                ('growth_strategy', models.CharField(choices=[('freeze', 'Freeze'), ('revise', 'Revise'), ('reset', 'Reset'), ('stack', 'Stack')], default='freeze', max_length=50)),
                ('task_definitions', models.JSONField(blank=True, default=dict)),
                ('is_current', models.BooleanField(default=False)),
                ('version', models.CharField(blank=True, max_length=50)),
                ('state', models.CharField(choices=[('pending', 'Pending'), ('growing', 'Growing'), ('complete', 'Complete'), ('error', 'Error')], default='pending', max_length=50)),
                ('dataset_type', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='+', to='contenttypes.contenttype')),
            ],
            options={
                'get_latest_by': 'created_at',
                'abstract': False,
            },
        ),
        migrations.AddField(
            model_name='batch',
            name='documents',
            field=models.ManyToManyField(related_name='_datatypes_batch_documents_+', through='datatypes.ProcessResult', to='datatypes.Document'),
        ),
        migrations.AddField(
            model_name='collection',
            name='dataset_version',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='datatypes.datasetversion'),
        ),
        migrations.AddField(
            model_name='document',
            name='dataset_version',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='datatypes.datasetversion'),
        ),
    ]