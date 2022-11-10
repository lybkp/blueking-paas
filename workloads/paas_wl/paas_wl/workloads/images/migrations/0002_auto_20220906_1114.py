# Generated by Django 3.2.12 on 2022-09-06 03:14

from django.db import migrations, models
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('images', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='appimagecredential',
            name='password',
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.CreateModel(
            name='AppUserCredential',
            fields=[
                ('uuid', models.UUIDField(auto_created=True, default=uuid.uuid4, editable=False, primary_key=True, serialize=False, unique=True, verbose_name='UUID')),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('updated', models.DateTimeField(auto_now=True)),
                ('application_id', models.UUIDField(verbose_name='所属应用')),
                ('name', models.CharField(help_text='凭证名称', max_length=32)),
                ('username', models.CharField(help_text='账号', max_length=64)),
                ('password', models.CharField(help_text='密码', max_length=255)),
                ('description', models.TextField(help_text='描述')),
            ],
            options={
                'unique_together': {('application_id', 'name')},
            },
        ),
    ]
