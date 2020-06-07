# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('my_bbs', '0003_auto_20200524_1554'),
    ]

    operations = [
        migrations.CreateModel(
            name='ReadRecord',
            fields=[
                ('id', models.AutoField(verbose_name='ID', primary_key=True, serialize=False, auto_created=True)),
                ('create_time', models.DateTimeField(verbose_name='创建时间', auto_now_add=True)),
                ('update_time', models.DateTimeField(verbose_name='更新时间', auto_now=True)),
                ('is_delete', models.BooleanField(verbose_name='删除标志', default=False)),
                ('user_id', models.IntegerField(verbose_name='用户id')),
                ('article_id', models.IntegerField(verbose_name='文章id')),
            ],
            options={
                'verbose_name': '浏览记录',
                'verbose_name_plural': '浏览记录',
                'db_table': 'read_record',
            },
        ),
    ]
