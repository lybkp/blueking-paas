# Generated by Django 2.2.17 on 2020-12-10 10:08

from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('api', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='AppAddOnTemplate',
            fields=[
                ('uuid', models.UUIDField(auto_created=True, default=uuid.uuid4, editable=False, primary_key=True, serialize=False, unique=True, verbose_name='UUID')),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('updated', models.DateTimeField(auto_now=True)),
                ('region', models.CharField(max_length=32)),
                ('name', models.CharField(max_length=64, verbose_name='模版名')),
                ('spec', models.TextField(verbose_name='资源内容')),
                ('enabled', models.BooleanField(default=True, verbose_name='资源启用')),
                ('type', models.IntegerField(default=1, verbose_name='挂件类型')),
            ],
            options={
                'unique_together': {('region', 'name')},
            },
        ),
        migrations.CreateModel(
            name='AppAddOn',
            fields=[
                ('uuid', models.UUIDField(auto_created=True, default=uuid.uuid4, editable=False, primary_key=True, serialize=False, unique=True, verbose_name='UUID')),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('updated', models.DateTimeField(auto_now=True)),
                ('enabled', models.BooleanField(default=True, verbose_name='是否启用')),
                ('spec', models.TextField(verbose_name='资源内容')),
                ('app', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='add_ons', to='api.App')),
                ('template', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='instances', to='resource_templates.AppAddOnTemplate')),
            ],
            options={
                'abstract': False,
            },
        ),
    ]
