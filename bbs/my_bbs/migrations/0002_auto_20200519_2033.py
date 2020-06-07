# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('my_bbs', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='tag',
            name='article',
            field=models.ManyToManyField(verbose_name='文章', to='my_bbs.Article'),
        ),
    ]
