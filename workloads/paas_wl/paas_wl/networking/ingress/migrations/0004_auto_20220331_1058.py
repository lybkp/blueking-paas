# Generated by Django 3.2.12 on 2022-03-31 02:58

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('services', '0003_auto_20211020_1556'),
    ]

    operations = [
        migrations.AlterField(
            model_name='appdomain',
            name='source',
            field=models.IntegerField(choices=[(1, 'BUILT_IN'), (2, 'AUTO_GEN'), (3, 'INDEPENDENT')]),
        ),
        migrations.CreateModel(
            name='Domain',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('region', models.CharField(help_text='部署区域', max_length=32)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('updated', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(help_text='域名', max_length=253)),
                ('path_prefix', models.CharField(default='/', help_text='the accessable path for current domain', max_length=64)),
                ('module_id', models.UUIDField(help_text='关联的模块 ID')),
                ('environment_id', models.BigIntegerField(help_text='关联的环境 ID')),
                ('lb_plan', models.CharField(default='LBDefaultPlan', max_length=64, verbose_name='load balancer plan')),
                ('https_enabled', models.NullBooleanField(default=False, help_text='该域名是否开启 https.')),
            ],
            options={
                'unique_together': {('name', 'path_prefix', 'module_id', 'environment_id')},
            },
        ),
    ]
