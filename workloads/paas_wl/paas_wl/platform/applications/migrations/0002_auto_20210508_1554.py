# Generated by Django 2.2.17 on 2021-05-08 07:54

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='buildprocess',
            name='int_requested_at',
            field=models.DateTimeField(help_text='用户请求中断的时间', null=True),
        ),
        migrations.AddField(
            model_name='buildprocess',
            name='logs_was_ready_at',
            field=models.DateTimeField(help_text='Pod 状态就绪允许读取日志的时间', null=True),
        ),
    ]
