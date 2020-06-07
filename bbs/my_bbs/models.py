from django.db import models
from django.contrib.auth.models import AbstractUser
from tinymce.models import HTMLField

# Create your models here.


class BaseModel(models.Model):
    '''基础模型表'''
    create_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    update_time = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    is_delete = models.BooleanField(default=False, verbose_name='删除标志')

    class Meta:
        # 说明是一个抽象类
        abstract = True


class User(AbstractUser, BaseModel):
    '''用户表'''
    class Meta:
        db_table = 'user_info'
        verbose_name = '用户'
        verbose_name_plural = verbose_name


class Article(BaseModel):
    '''文章表'''
    title = models.CharField(max_length=128, verbose_name='标题')
    desc = models.CharField(max_length=128, verbose_name='简介')
    image = models.ImageField(upload_to='article', verbose_name='图片')
    up_num = models.IntegerField(default=0, verbose_name='点赞数')
    comment_num = models.IntegerField(default=0, verbose_name='评论数')
    read_num = models.IntegerField(default=0, verbose_name='阅读量')
    article_detail = models.ForeignKey('ArticleDetail', verbose_name='文章详情')
    sort = models.ForeignKey('Sort', verbose_name='文章分类')
    author = models.ForeignKey('User', verbose_name='作者')

    def __str__(self):
        return self.title

    class Meta:
        db_table = 'article'
        verbose_name = '文章'
        verbose_name_plural = verbose_name


class ArticleDetail(BaseModel):
    '''文章详情表'''
    content = HTMLField(verbose_name='文章详情')

    class Meta:
        db_table = 'article_detail'
        verbose_name = '文章详情'
        verbose_name_plural = verbose_name


class Sort(BaseModel):
    '''文章分类'''
    name = models.CharField(max_length=128, verbose_name='分类名')
    desc = models.CharField(max_length=256, verbose_name='简介')
    parent = models.ForeignKey('Sort', null=True, blank=True ,verbose_name='父级分类')

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = '分类'
        verbose_name_plural = verbose_name


class Tag(BaseModel):
    '''标签类'''
    name = models.CharField(max_length=128, verbose_name='标签名')
    desc = models.CharField(max_length=512, verbose_name='简介')
    article = models.ManyToManyField('Article', blank=True, verbose_name='文章')

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'tag'
        verbose_name = '标签'
        verbose_name_plural = verbose_name


class Comment(BaseModel):
    '''评论类'''
    article = models.ForeignKey('Article', verbose_name='文章')
    user = models.ForeignKey('User', verbose_name='用户')
    content = models.CharField(max_length=1024, verbose_name='评论内容')
    parent = models.ForeignKey('Comment', null=True, blank=True, verbose_name='父级评论')
    up_num = models.IntegerField(default=0, verbose_name='点赞量')
    weight = models.IntegerField(default=0, verbose_name='权重')

    def __str__(self):
        return self.article.title

    class Meta:
        db_table = 'comment'
        verbose_name = '评论'
        verbose_name_plural = verbose_name


class ArticleUp(BaseModel):
    '''文章点赞类'''
    UP_OR_DOWN_CHOICES = (
        (1, '点赞'),
        (0, '点踩')
    )

    up_or_down = models.SmallIntegerField(choices=UP_OR_DOWN_CHOICES, verbose_name='赞或踩')
    article = models.ForeignKey('Article', verbose_name='文章')
    user = models.ForeignKey('User', verbose_name='用户')

    class Meta:
        db_table = 'article_up'
        verbose_name = '文章点赞'
        verbose_name_plural = verbose_name


class CommentUp(BaseModel):
    '''评论点赞类'''
    UP_OR_DOWN_CHOICES = (
        (1, '点赞'),
        (0, '点踩')
    )

    up_or_down = models.SmallIntegerField(choices=UP_OR_DOWN_CHOICES, verbose_name='赞或踩')
    comment = models.ForeignKey('Comment', verbose_name='评论')
    user = models.ForeignKey('User', verbose_name='用户')

    class Meta:
        db_table = 'comment_up'
        verbose_name = '评论点赞'
        verbose_name_plural = verbose_name


class PromotionArticle(BaseModel):
    '''首页轮播图'''
    image = models.ImageField(upload_to='article', verbose_name='轮播图')
    article = models.ForeignKey('Article')
    index = models.SmallIntegerField(verbose_name='索引')

    class Meta:
        db_table = 'promotion_article'
        verbose_name = '轮播'
        verbose_name_plural = verbose_name


class ReadRecord(BaseModel):
    '''用户浏览记录'''
    user_id = models.IntegerField(verbose_name='用户id')
    article_id = models.IntegerField(verbose_name='文章id')

    class Meta:
        db_table = 'read_record'
        verbose_name = '浏览记录'
        verbose_name_plural = verbose_name