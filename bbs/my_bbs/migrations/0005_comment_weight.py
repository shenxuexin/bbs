# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('my_bbs', '0004_readrecord'),
    ]

    operations = [
        migrations.AddField(
            model_name='comment',
            name='weight',
            field=models.IntegerField(verbose_name='权重', default=0),
        ),
    ]
