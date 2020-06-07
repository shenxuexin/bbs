from django import template
from my_bbs.views import create_pages
from my_bbs.models import Sort, Tag, Article
from django.db.models import Count

register = template.Library()


@register.filter
def double(num):
    if num < 10:
        return '0'+str(num)
    else:
        return num


@register.filter
def tran_to_page_range(paginator, pindex):
    page, page_range = create_pages(paginator, pindex)
    return page_range


@register.filter
def get_sorts(sorts):
    if sorts:
        return sorts
    else:
        sorts = Sort.objects.filter(parent=None)
        for sort in sorts:
            child_sorts = Sort.objects.filter(parent=sort)

            if child_sorts:
                sort.child_sorts = child_sorts
        return sorts


@register.filter
def get_tags(tags):
    if tags:
        return tags
    else:
        return Tag.objects.all()


@register.filter
def get_dates(dates):
    date_list = Article.objects.all().extra(
        select={'date_ym': 'date_format(create_time, "%%Y年%%m月")'}
    ).values('date_ym').annotate(num_article=Count('id'))

    return date_list