# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('my_bbs', '0002_auto_20200519_2033'),
    ]

    operations = [
        migrations.CreateModel(
            name='PromotionArticle',
            fields=[
                ('id', models.AutoField(verbose_name='ID', primary_key=True, serialize=False, auto_created=True)),
                ('create_time', models.DateTimeField(verbose_name='创建时间', auto_now_add=True)),
                ('update_time', models.DateTimeField(verbose_name='更新时间', auto_now=True)),
                ('is_delete', models.BooleanField(verbose_name='删除标志', default=False)),
                ('image', models.ImageField(verbose_name='轮播图', upload_to='article')),
                ('index', models.SmallIntegerField(verbose_name='索引')),
                ('article', models.ForeignKey(to='my_bbs.Article')),
            ],
            options={
                'verbose_name': '轮播',
                'verbose_name_plural': '轮播',
                'db_table': 'promotion_article',
            },
        ),
        migrations.AlterModelOptions(
            name='sort',
            options={'verbose_name': '分类', 'verbose_name_plural': '分类'},
        ),
    ]
