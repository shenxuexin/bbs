from django.contrib import admin
from my_bbs.models import *


class ArticleAdmin(admin.ModelAdmin):
    list_display = ['title']


class SortAdmin(admin.ModelAdmin):
    list_display = ['name', 'parent']


class TagAdmin(admin.ModelAdmin):
    list_display = ['name']


class CommentAdmin(admin.ModelAdmin):
    list_display = ['id', 'content']


class PromotionAdmin(admin.ModelAdmin):
    list_display = ['id', 'article']


# Register your models here.
admin.site.register(Article, ArticleAdmin)
admin.site.register(ArticleDetail)
admin.site.register(Sort, SortAdmin)
admin.site.register(Tag, TagAdmin)
admin.site.register(Comment, CommentAdmin)
admin.site.register(PromotionArticle, PromotionAdmin)
