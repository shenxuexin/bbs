# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('my_bbs', '0005_comment_weight'),
    ]

    operations = [
        migrations.AlterField(
            model_name='tag',
            name='article',
            field=models.ManyToManyField(verbose_name='文章', blank=True, to='my_bbs.Article'),
        ),
        migrations.AlterField(
            model_name='tag',
            name='desc',
            field=models.CharField(verbose_name='简介', max_length=512),
        ),
    ]
