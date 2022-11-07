# Generated by Django 2.2.17 on 2020-12-10 10:08

import paas_wl.platform.applications.models.build
import paas_wl.platform.applications.models.validators
import paas_wl.utils.models
from django.db import migrations, models
import django.db.models.deletion
import jsonfield.fields
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='App',
            fields=[
                (
                    'uuid',
                    models.UUIDField(
                        auto_created=True,
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                        unique=True,
                        verbose_name='UUID',
                    ),
                ),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('updated', models.DateTimeField(auto_now=True)),
                ('owner', models.CharField(max_length=64)),
                ('region', models.CharField(max_length=32)),
                (
                    'name',
                    models.SlugField(
                        max_length=64,
                        validators=[paas_wl.platform.applications.models.validators.validate_app_name],
                    ),
                ),
                (
                    'structure',
                    jsonfield.fields.JSONField(
                        blank=True,
                        default={},
                        validators=[paas_wl.platform.applications.models.validators.validate_app_structure],
                    ),
                ),
            ],
            options={
                'unique_together': {('region', 'name')},
            },
        ),
        migrations.CreateModel(
            name='Build',
            fields=[
                (
                    'uuid',
                    models.UUIDField(
                        auto_created=True,
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                        unique=True,
                        verbose_name='UUID',
                    ),
                ),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('updated', models.DateTimeField(auto_now=True)),
                ('owner', models.CharField(max_length=64)),
                ('slug_path', models.TextField()),
                ('source_type', models.CharField(max_length=128, null=True)),
                ('branch', models.CharField(max_length=128, null=True)),
                ('revision', models.CharField(max_length=128, null=True)),
                (
                    'procfile',
                    jsonfield.fields.JSONField(
                        blank=True, default={}, validators=[paas_wl.utils.models.validate_procfile]
                    ),
                ),
                ('app', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='api.App')),
            ],
            options={
                'ordering': ['-created'],
                'get_latest_by': 'created',
            },
        ),
        migrations.CreateModel(
            name='Config',
            fields=[
                (
                    'uuid',
                    models.UUIDField(
                        auto_created=True,
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                        unique=True,
                        verbose_name='UUID',
                    ),
                ),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('updated', models.DateTimeField(auto_now=True)),
                ('owner', models.CharField(max_length=64)),
                ('values', jsonfield.fields.JSONField(blank=True, default={})),
                ('resource_requirements', jsonfield.fields.JSONField(blank=True, default={})),
                ('node_selector', jsonfield.fields.JSONField(blank=True, default={})),
                ('domain', models.CharField(default='', max_length=64, verbose_name='domain')),
                ('tolerations', jsonfield.fields.JSONField(blank=True, default={})),
                ('cluster', models.CharField(blank=True, default='', max_length=64)),
                ('image', models.CharField(max_length=256, null=True)),
                ('metadata', jsonfield.fields.JSONField(blank=True, null=True)),
                ('app', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='api.App')),
            ],
            options={
                'ordering': ['-created'],
                'get_latest_by': 'created',
                'unique_together': {('app', 'uuid')},
            },
        ),
        migrations.CreateModel(
            name='OutputStream',
            fields=[
                (
                    'uuid',
                    models.UUIDField(
                        auto_created=True,
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                        unique=True,
                        verbose_name='UUID',
                    ),
                ),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('updated', models.DateTimeField(auto_now=True)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='OutputStreamLine',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('stream', models.CharField(max_length=16)),
                ('line', models.TextField()),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('updated', models.DateTimeField(auto_now=True)),
                (
                    'output_stream',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, related_name='lines', to='api.OutputStream'
                    ),
                ),
            ],
            options={
                'ordering': ['created'],
            },
        ),
        migrations.CreateModel(
            name='OneOffCommand',
            fields=[
                (
                    'uuid',
                    models.UUIDField(
                        auto_created=True,
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                        unique=True,
                        verbose_name='UUID',
                    ),
                ),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('updated', models.DateTimeField(auto_now=True)),
                ('operator', models.CharField(max_length=64, null=True)),
                ('command', models.TextField()),
                ('exit_code', models.SmallIntegerField(null=True, verbose_name='ExitCode')),
                ('build', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='api.Build')),
                (
                    'output_stream',
                    models.OneToOneField(
                        null=True, on_delete=django.db.models.deletion.CASCADE, to='api.OutputStream'
                    ),
                ),
            ],
            options={
                'ordering': ['created'],
                'get_latest_by': 'created',
            },
        ),
        migrations.CreateModel(
            name='BuildProcess',
            fields=[
                (
                    'uuid',
                    models.UUIDField(
                        auto_created=True,
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                        unique=True,
                        verbose_name='UUID',
                    ),
                ),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('updated', models.DateTimeField(auto_now=True)),
                ('owner', models.CharField(max_length=64)),
                ('image', models.CharField(max_length=256, null=True)),
                ('buildpacks', jsonfield.fields.JSONCharField(max_length=4096, null=True)),
                ('source_tar_path', models.CharField(max_length=2048)),
                ('branch', models.CharField(max_length=128, null=True)),
                ('revision', models.CharField(max_length=128, null=True)),
                (
                    'status',
                    models.CharField(
                        choices=[('successful', 'SUCCESSFUL'), ('failed', 'FAILED'), ('pending', 'PENDING')],
                        default='pending',
                        max_length=12,
                    ),
                ),
                ('app', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='api.App')),
                (
                    'build',
                    models.OneToOneField(
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='build_process',
                        to='api.Build',
                    ),
                ),
                (
                    'output_stream',
                    models.OneToOneField(
                        null=True, on_delete=django.db.models.deletion.CASCADE, to='api.OutputStream'
                    ),
                ),
            ],
            options={
                'ordering': ['-created'],
                'get_latest_by': 'created',
            },
        ),
        migrations.CreateModel(
            name='Release',
            fields=[
                (
                    'uuid',
                    models.UUIDField(
                        auto_created=True,
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                        unique=True,
                        verbose_name='UUID',
                    ),
                ),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('updated', models.DateTimeField(auto_now=True)),
                ('owner', models.CharField(max_length=64)),
                ('version', models.PositiveIntegerField()),
                ('summary', models.TextField(blank=True, null=True)),
                ('failed', models.BooleanField(default=False)),
                ('app', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='api.App')),
                ('build', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='api.Build')),
                ('config', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='api.Config')),
            ],
            options={
                'ordering': ['-created'],
                'get_latest_by': 'created',
                'unique_together': {('app', 'version')},
            },
        ),
    ]
