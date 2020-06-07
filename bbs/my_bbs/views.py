from django.shortcuts import render, redirect
from django.views.generic import View
from django.http import HttpResponse, JsonResponse
from django.core.urlresolvers import reverse
from django.core.paginator import Paginator
from django.conf import settings
from django.core.mail import send_mail
from django.contrib.auth import login, logout, authenticate
from django.db.models import Q, Count
from django.db import transaction

import markdown
from celery_task.tasks import send_active_mail
from fdfs_client.client import Fdfs_client
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer, SignatureExpired
from my_bbs.models import User, Article, ArticleDetail, ArticleUp, Comment, Tag, Sort, PromotionArticle, ReadRecord
import re


def create_context(request):
    '''构建上下文'''
    tags = Tag.objects.all()
    sorts = Sort.objects.filter(parent=None)
    for sort in sorts:
        child_sorts = Sort.objects.filter(parent=sort)

        if child_sorts:
            sort.child_sorts = child_sorts

    # 日期归档
    date_list = create_date_list()

    # 当前路径
    context = {
        'tags': tags,
        'sorts': sorts,
        'date_list': date_list,
        'cur_path': request.get_full_path()
    }

    return context


def create_pages(paginator, page_index):
    '''生成页面和页码'''
    all_page_num = paginator.num_pages
    try:
        page_index = int(page_index)
    except Exception as e:
        page_index = 1

    if page_index > all_page_num:
        page_index = 1
    elif page_index < 1:
        page_index = 1

    page = paginator.page(page_index)

    show_num = settings.SHOW_PAGE_NUM
    half_num = (settings.SHOW_PAGE_NUM + 1) / 2

    if all_page_num <= show_num:
        page_range = range(1, all_page_num + 1)
    elif page_index <= half_num:
        page_range = range(1, show_num + 1)
    elif page_index >= all_page_num - half_num - 1:
        page_range = range(all_page_num - show_num + 1, all_page_num + 1)
    else:
        page_range = range(page_index - half_num + 1, page_index + half_num)

    return page, page_range


def create_date_list():
    date_list = Article.objects.all().extra(
        select={'date_ym': 'date_format(create_time, "%%Y年%%m月")'}
    ).values('date_ym').annotate(num_article=Count('id'))

    return date_list


def superuser_require(func):
    def wrapper(self, request, *args, **kwargs):
        user = request.user
        if not user.is_authenticated():
            return redirect(reverse('my_bbs:login'))
        elif user.username not in settings.SUPER_USER:
            return redirect(reverse('my_bbs:index'))
        else:
            return func(self, request, *args, **kwargs)
    return wrapper


# Create your views here.
class IndexView(View):
    '''首页'''
    def get(self, request):
        articles = Article.objects.all()
        promotions = PromotionArticle.objects.all().order_by('index')

        # 分页
        paginator = Paginator(articles, settings.PER_PAGE)
        page_index = request.GET.get('page')

        page, page_range = create_pages(paginator, page_index)

        context = create_context(request)

        context['articles'] = page
        context['promotions'] = promotions
        context['page'] = 'index'
        context['page_range'] = page_range
        context['link_type'] = 'index'

        return render(request, 'index.html', context)


class TagListView(View):
    '''标签列表页'''
    def get(self, request, tag_id):
        try:
            tag = Tag.objects.get(id=tag_id)
        except Tag.DoesNotExist:
            return redirect(reverse('my_bbs:index'))

        articles = Article.objects.filter(tag=tag)
        promotions = PromotionArticle.objects.all().order_by('index')

        # 分页
        paginator = Paginator(articles, settings.PER_PAGE)
        page_index = request.GET.get('page')

        page, page_range = create_pages(paginator, page_index)

        context = create_context(request)
        context['articles'] = page
        context['promotions'] = promotions
        context['page_range'] = page_range
        context['link_type'] = 'tag'
        context['tag'] = tag

        return render(request, 'tag_list.html', context)


class SortListView(View):
    '''分类列表页'''
    def get(self, request, sort_id):
        try:
            sort = Sort.objects.get(id=sort_id)
        except Sort.DoesNotExist:
            return redirect(reverse('my_bbs:index'))

        sort_parent_name = None
        if sort.parent:
            sort_parent_name = sort.parent.name

        articles = Article.objects.filter(Q(sort=sort) | Q(sort__parent=sort))
        promotions = PromotionArticle.objects.all().order_by('index')

        # 分页
        paginator = Paginator(articles, settings.PER_PAGE)
        page_index = request.GET.get('page')

        page, page_range = create_pages(paginator, page_index)

        context = create_context(request)
        context['articles'] = page
        context['promotions'] = promotions
        context['page'] = sort.name
        context['sort_parent'] = sort_parent_name
        context['page_range'] = page_range
        context['link_type'] = 'sort'
        context['sort_id'] = sort.id

        return render(request, 'sort_list.html', context)


class DateListView(View):
    '''日期归档'''
    def get(self, request, date):
        context = create_context(request)

        date_list = Article.objects.all().extra(
            select={'date_ym': 'date_format(create_time, "%%Y年%%m月")'}
        )

        articles = []
        for article_obj in date_list:
            if article_obj.date_ym == date:
                articles.append(article_obj)

        # 分页
        paginator = Paginator(articles, settings.PER_PAGE)
        page_index = request.GET.get('page')

        page, page_range = create_pages(paginator, page_index)

        context['articles'] = page
        context['date'] = date
        context['link_type'] = 'date'
        context['page_range'] = page_range

        return render(request, 'date_list.html', context)


class RegisterView(View):
    '''注册视图类'''
    def get(self, request):
        return render(request, 'register.html')

    def post(self, request):
        # 获取数据
        username = request.POST.get('username')
        pwd = request.POST.get('pwd')
        email = request.POST.get('email')

        # 数据校验
        if not all([username, pwd, email]):
            return render(request, 'register.html', {'errmsg': '数据不完整'})

        if not re.match(r'^\w+([-+.]\w+)*@\w+([-.]\w+)*\.\w+([-.]\w+)*$', email):
            return render(request, 'register.html', {'errmsg': '邮箱格式错误'})

        # 验证是否已经注册
        try:
            user_obj = User.objects.get(username=username)
        except User.DoesNotExist:
            user_obj = None

        if user_obj:
            # 用户已存在
            return render(request, 'register.html', {'errmsg': '用户已存在'})

        # 业务处理: 注册用户, 发送激活邮件
        user = User.objects.create_user(username, email, pwd)
        user.is_active = False
        user.save()

        # 设置激活地址: http://192.168.153.131:8000/user/active/user_id
        serializer = Serializer(settings.SECRET_KEY, 3600*2)
        info = {'confirm': user.id}
        token = serializer.dumps(info).decode('utf-8')

        # 发送邮件
        send_active_mail.delay(email, token)

        # 返回响应
        return redirect(reverse('my_bbs:index'))


class AcitveView(View):
    '''激活视图'''
    def get(self, request, token):
        serializer = Serializer(settings.SECRET_KEY, 3600*2)
        try:
            # 获取激活信息
            info = serializer.loads(token)
            user_id = info['confirm']

            # 更改激活状态
            try:
                user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                return HttpResponse('用户不存在')

            user.is_active = True
            user.save()
            return redirect(reverse('my_bbs:login'))

        except SignatureExpired:
            return HttpResponse('链接已过期')


class LoginView(View):
    '''登录视图类'''
    def get(self, request):
        if 'username' in request.COOKIES:
            username = request.COOKIES.get('username')
            checked = 'checked'
        else:
            username = ''
            checked = ''
        return render(request, 'login.html', {'username': username, 'checked': checked})

    def post(self, request):
        # 获取数据
        username = request.POST.get('username')
        pwd = request.POST.get('pwd')
        remember = request.POST.get('remember')

        # 数据校验
        if not all([username, pwd]):
            return render(request, 'login.html', {'errmsg': '必填项不能为空'})

        # 业务处理:登录校验
        user = authenticate(username=username, password=pwd)
        if user is not None:
            if user.is_active:
                # 用户已激活->登录
                # 记录登录状态
                login(request, user)

                # 获取目标地址
                next_url = request.GET.get('next', reverse('my_bbs:index'))

                # 跳转
                response = redirect(next_url)

                # 设置cookie
                if remember == 'on':
                    response.set_cookie('username', username, max_age=3600*2)
                else:
                    response.delete_cookie('username')

                # 返回页面
                return response
            else:
                return render(request, 'login.html', {'errmsg': '用户未激活'})
        else:
            return render(request, 'login.html', {'errmsg': '用户名或密码错误'})


class LogoutView(View):
    '''登出'''
    def get(self, request):
        logout(request)

        # 获取当前地址
        next_url = request.GET.get('next', reverse('my_bbs:index'))

        return redirect(next_url)


class DetailView(View):
    '''详情页'''
    @transaction.atomic
    def get(self, request, article_id):
        try:
            article = Article.objects.get(id=article_id)
        except Article.DoesNotExist:
            return redirect(reverse('my_bbs:index'))

        sort_parent_name = None
        if article.sort.parent:
            sort_parent_name = article.sort.parent.name

        # 增加阅读量
        user = request.user
        if user.is_authenticated():
            try:
                # 用户已经浏览过
                record = ReadRecord.objects.get(user_id=user.id, article_id=article_id)
            except Exception as e:
                # 用户未浏览过

                ReadRecord.objects.create(user_id=user.id, article_id=article_id)
                article.read_num += 1
                article.save()
        else:
            # 游客浏览量直接+1,用户id记为0
            ReadRecord.objects.create(user_id=0, article_id=article.id)
            article.read_num += 1
            article.save()

        comments = Comment.objects.filter(article=article).order_by('-weight', '-create_time')
        article.comments = comments

        context = create_context(request)
        # 查询是否点赞/点踩
        if user.is_authenticated():
            try:
                up_down = ArticleUp.objects.get(user=user, article=article)
            except ArticleUp.DoesNotExist:
                context['up_down'] = -1
            else:
                context['up_down'] = up_down.up_or_down   # 1赞0踩

        context['page'] = article.sort.name
        context['article'] = article
        context['sort_parent'] = sort_parent_name

        return render(request, 'detail.html', context)


class CommentView(View):
    '''评论处理视图'''
    def post(self, request):
        # 验证登录
        user = request.user
        if not user.is_authenticated():
            return JsonResponse({'code': 0, 'errmsg': '用户未登录'})

        # 接收数据
        comment = request.POST.get('comment')
        article_id = request.POST.get('article_id')

        # 数据校验
        if not all([comment, article_id]):
            return JsonResponse({'code': 1, 'errmsg': '数据不完整'})

        try:
            article = Article.objects.get(id=article_id)
        except Article.DoesNotExist:
            return JsonResponse({'code': 2, 'errmsg': '用户不存在'})

        # 业务处理:添加评论
        Comment.objects.create(article=article, user=user, content=comment, up_num=0)

        # 更改文章的评论数
        article.comment_num += 1
        article.save()

        # 返回响应
        return JsonResponse({'code': 3, 'msg': '评论成功!'})


class CenterArticleView(View):
    '''用户中心-文章管理'''
    @superuser_require
    def get(self, request):
        context = create_context(request)

        sort_id = request.GET.get('sort_id')

        if sort_id is None or sort_id == '-1':
            articles = Article.objects.all()
        else:
            try:
                sort_id = int(sort_id)
                sort = Sort.objects.get(id=sort_id)
            except Sort.DoesNotExist:
                articles = Article.objects.all()
            else:
                articles = Article.objects.filter(Q(sort=sort) | Q(sort__parent=sort))

        all_sorts = Sort.objects.all()

        context['active_sort'] = 'article'
        context['articles'] = articles
        context['page'] = 'center'
        context['all_sorts'] = all_sorts
        context['sort_id'] = sort_id

        return render(request, 'center_article.html', context)


class CreateArticleView(View):
    '''创建博文'''
    @superuser_require
    def get(self, request):
        all_sorts = Sort.objects.all()

        context = create_context(request)
        context['page'] = 'center'
        context['all_sorts'] = all_sorts

        return render(request, 'new_article.html', context)

    def post(self, request):
        # 校验登录
        user = request.user
        if not user.is_authenticated():
            return JsonResponse({'code':0, 'errmsg': '用户未登录'})

        # 获取数据
        title = request.POST.get('title')
        desc = request.POST.get('desc')
        cover = request.FILES.get('cover')
        sort_id = request.POST.get('sort')
        tag_ids = request.POST.getlist('tag')
        content = request.POST.get('content-editormd-markdown-doc')

        # 数据校验
        if not all([title, desc, cover, sort_id, content]):
            return JsonResponse({'code':1, 'errmsg': '数据不完整'})

        try:
            sort = Sort.objects.get(id=sort_id)
        except Sort.DoesNotExist:
            return JsonResponse({'code':2, 'errmsg': '分类不存在'})

        tags = []
        try:
            for tag_id in tag_ids:
                tag_id = int(tag_id)
                tag = Tag.objects.get(id=tag_id)
                tags.append(tag)
        except Tag.DoesNotExist:
            return JsonResponse({'code':3, 'errmsg': '标签不存在'})

        # 业务处理: 添加新文章
        # 创建文章详情
        try:
            detail = ArticleDetail.objects.create(content=content)
        except Exception as e:
            return JsonResponse({'code':4, 'errmsg': '文章创建失败01'})

        # 上传图片
        try:
            client = Fdfs_client(settings.FDFS_CLIENT_CONFIG)
            result = client.upload_by_buffer(cover.read())

            if result.get('Status') != 'Upload successed.':
                return JsonResponse({'code':5, 'errmsg': '图片上传失败01'})

            filename = result.get('Remote file_id')
        except Exception as e:
            return JsonResponse({'code':6, 'errmsg': '图片上传失败02'})

        # 创建文章
        try:
            article = Article.objects.create(
                title=title,
                desc=desc,
                image=filename,
                article_detail=detail,
                sort=sort,
                author=user
            )
        except Exception as e:
            return JsonResponse({'code':7, 'errmsg': '文章创建失败02'})

        # 添加标签
        try:
            for tag in tags:
                article.tag_set.add(tag)
        except Exception as e:
            return JsonResponse({'code': 8, 'errmsg': '标签添加失败'})

        # 返回响应
        return JsonResponse({'code':9, 'dir_url': reverse('my_bbs:detail', kwargs={'article_id': article.id})})


class EditArticleView(View):
    '''编辑博文'''
    @superuser_require
    def get(self, request, aid):
        try:
            article = Article.objects.get(id=int(aid))
        except Exception as e:
            return redirect('my_bbs:article_manage')

        all_sorts = Sort.objects.all()

        context = create_context(request)
        context['page'] = 'center'
        context['all_sorts'] = all_sorts
        context['article'] = article

        return render(request, 'edit_article.html', context)

    def post(self, request, aid):
        # 校验登录
        user = request.user
        if not user.is_authenticated():
            return JsonResponse({'code':0, 'errmsg': '用户未登录'})

        # 获取数据
        aid = request.POST.get('aid')
        title = request.POST.get('title')
        desc = request.POST.get('desc')
        cover = request.FILES.get('cover')
        sort_id = request.POST.get('sort')
        tag_ids = request.POST.getlist('tag')
        content = request.POST.get('content-editormd-markdown-doc')

        # 数据校验
        try:
            aid = int(aid)
        except Exception as e:
            return JsonResponse({'code':1, 'errmsg': '无效的文章id'})

        try:
            article = Article.objects.get(id=aid)
        except Article.DoesNotExist:
            return JsonResponse({'code':2, 'errmsg': '文章不存在'})

        if sort_id:
            try:
                sort_id = int(sort_id)
            except Exception as e:
                return JsonResponse({'code':3, 'errmsg': '无效的分类id'})

            try:
                sort = Sort.objects.get(id=sort_id)
            except Sort.DoesNotExist:
                return JsonResponse({'code':4, 'errmsg': '分类不存在'})

            article.sort = sort

        tags = []
        try:
            for tag_id in tag_ids:
                tag_id = int(tag_id)
                tag = Tag.objects.get(id=tag_id)
                tags.append(tag)
        except Tag.DoesNotExist:
            return JsonResponse({'code':3, 'errmsg': '标签不存在'})

        # 业务处理: 添加新文章
        # 上传图片
        if cover:
            try:
                client = Fdfs_client(settings.FDFS_CLIENT_CONFIG)
                result = client.upload_by_buffer(cover.read())

                if result.get('Status') != 'Upload successed.':
                    return JsonResponse({'code':5, 'errmsg': '图片上传失败01'})

                filename = result.get('Remote file_id')
            except Exception as e:
                return JsonResponse({'code':6, 'errmsg': '图片上传失败02'})

            article.image = filename

        # 更新标题, 简介, 内容
        if title != article.title:
            article.title = title

        if desc != article.desc:
            article.desc = desc

        if content != article.article_detail.content:
            article.article_detail.content = content

        # 添加标签
        try:
            for tag in tags:
                if tag not in article.tag_set.all():
                    article.tag_set.add(tag)
            for in_tag in article.tag_set.all():
                if in_tag not in tags:
                    article.tag_set.remove(in_tag)
        except Exception as e:
            return JsonResponse({'code': 7, 'errmsg': '标签更新失败'})

        # 保存更新
        article.article_detail.save()
        article.save()

        # 返回响应
        return JsonResponse({'code':8, 'dir_url': reverse('my_bbs:detail', kwargs={'article_id': article.id})})


class DelArticleView(View):
    '''删除文章视图'''
    def post(self, request):
        # 校验登录
        user = request.user
        if not user.is_authenticated():
            return JsonResponse({'code':0, 'errmsg': '用户未登录'})

        # 获取数据
        a_id = request.POST.get('a_id')

        # 校验数据
        if not a_id:
            return JsonResponse({'code':1, 'errmsg': '无效的文章id'})

        try:
            article = Article.objects.get(id=a_id)
        except Article.DoesNotExist:
            return JsonResponse({'code':2, 'errmsg': '文章不存在'})

        # 业务处理: 删除文章
        try:
            ArticleDetail.objects.get(article=article).delete()
            article.delete()
        except Exception as e:
            return JsonResponse({'code':3, 'errmsg': '删除失败'})

        # 返回响应
        return JsonResponse({'code':4, 'msg': '删除成功'})


class CenterCommentView(View):
    '''用户中心-评论'''
    @superuser_require
    def get(self, request):
        context = create_context(request)

        sort_id = request.GET.get('sort_id')

        if sort_id is None or sort_id == '-1':
            comments = Comment.objects.all()
        else:
            try:
                sort_id = int(sort_id)
                sort = Sort.objects.get(id=sort_id)
            except Sort.DoesNotExist:
                comments = Comment.objects.all()
            else:
                comments = Comment.objects.filter(Q(article__sort=sort) | Q(article__sort__parent=sort))

        comments = comments.order_by('-weight', 'article_id', '-create_time')
        all_sorts = Sort.objects.all()

        context['active_sort'] = 'comment'
        context['comments'] = comments
        context['page'] = 'center'
        context['all_sorts'] = all_sorts
        context['sort_id'] = sort_id

        return render(request, 'center_comment.html', context)


class DelCommentView(View):
    '''删除评论'''
    def post(self, request):
        # 校验登录
        user = request.user
        if not user.is_authenticated():
            return JsonResponse({'code': 0, 'errmsg': '用户未登录'})

        # 接收数据
        cid = request.POST.get('cid')

        # 校验数据
        if not cid:
            return JsonResponse({'code': 1, 'errmsg': '无效的评论id'})

        try:
            comment = Comment.objects.get(id=cid)
        except Comment.DoesNotExist:
            return JsonResponse({'code': 2, 'errmsg': '评论不存在'})

        # 业务处理: 删除评论
        try:
            comment.delete()
        except Exception as e:
            return JsonResponse({'code': 3, 'errmsg': '评论删除失败'})

        # 返回响应
        return JsonResponse({'code': 4, 'msg': '删除成功'})


class TopCommentView(View):
    '''置顶评论'''
    def post(self, request):
        # 校验登录
        user = request.user
        if not user.is_authenticated():
            return JsonResponse({'code': 0, 'errmsg': '用户未登录'})

        # 接收数据
        cid = request.POST.get('cid')

        # 校验数据
        if not cid:
            return JsonResponse({'code': 1, 'errmsg': '无效的评论id'})

        try:
            comment = Comment.objects.get(id=cid)
        except Comment.DoesNotExist:
            return JsonResponse({'code': 2, 'errmsg': '评论不存在'})

        # 业务处理: 置顶
        try:
            comment.weight = 99
            comment.save()
        except Exception as e:
            return JsonResponse({'code': 3, 'errmsg': '评论置顶失败'})

        # 返回响应
        return JsonResponse({'code': 4, 'msg': '置顶成功'})


class DownCommentView(View):
    '''取消置顶'''
    def post(self, request):
        # 校验登录
        user = request.user
        if not user.is_authenticated():
            return JsonResponse({'code': 0, 'errmsg': '用户未登录'})

        # 接收数据
        cid = request.POST.get('cid')

        # 校验数据
        if not cid:
            return JsonResponse({'code': 1, 'errmsg': '无效的评论id'})

        try:
            comment = Comment.objects.get(id=cid)
        except Comment.DoesNotExist:
            return JsonResponse({'code': 2, 'errmsg': '评论不存在'})

        # 业务处理: 置顶
        try:
            comment.weight = 0
            comment.save()
        except Exception as e:
            return JsonResponse({'code': 3, 'errmsg': '取消置顶失败'})

        # 返回响应
        return JsonResponse({'code': 4, 'msg': '取消置顶成功'})


class CenterSortView(View):
    '''用户中心-分类'''
    @superuser_require
    def get(self, request):
        context = create_context(request)

        all_sorts = Sort.objects.all().order_by('parent')

        context['active_sort'] = 'sort'
        context['page'] = 'center'
        context['all_sorts'] = all_sorts

        return render(request, 'center_sort.html', context)


class DelSortView(View):
    '''删除分类'''
    def post(self, request):
        # 校验登录
        user = request.user
        if not user.is_authenticated():
            return JsonResponse({'code': 0, 'errmsg': '用户未登录'})

        # 接收数据
        sid = request.POST.get('sid')

        # 校验数据
        if not sid:
            return JsonResponse({'code': 1, 'errmsg': '无效的分类id'})

        try:
            sort = Sort.objects.get(id=sid)
        except Sort.DoesNotExist:
            return JsonResponse({'code': 2, 'errmsg': '分类不存在'})

        # 业务处理: 删除分类
        try:
            Sort.objects.filter(parent=sort).delete()
            sort.delete()
        except Exception as e:
            return JsonResponse({'code': 3, 'errmsg': '分类删除失败'})

        # 返回响应
        return JsonResponse({'code': 4, 'msg': '删除成功'})


class CreateSortView(View):
    '''新建分类'''
    def post(self, request):
        # 验证登录
        user = request.user
        if not user.is_authenticated():
            return JsonResponse({'code':0, 'errmsg': '用户未登录'})

        # 获取数据
        sort_name = request.POST.get('sort_name')
        sort_desc = request.POST.get('sort_desc')
        parent_id = request.POST.get('parent_id')

        # 数据校验
        if not all([sort_name, parent_id, sort_desc]):
            return JsonResponse({'code': 1, 'errmsg': '数据不完整'})

        # 当前分类是否存在
        try:
            is_exists = Sort.objects.get(name=sort_name)
        except Sort.DoesNotExist:
            is_exists = None

        if is_exists:
            return JsonResponse({'code': 2, 'errmsg': '分类已存在'})

        # 父分类是否存在
        sort_parent = None
        if parent_id != '-1':
            try:
                sort_parent = Sort.objects.get(id=parent_id)
            except Sort.DoesNotExist:
                return JsonResponse({'code': 3, 'errmsg': '父级分类不存在'})

        # 业务处理: 创建分类
        try:
            sort = Sort.objects.create(name=sort_name, desc=sort_desc, parent=sort_parent)
        except Exception as e:
            return JsonResponse({'code': 4, 'errmsg': '创建分类失败'})

        # 返回响应
        return JsonResponse({'code': 5, 'msg': '创建成功', 'sid': sort.id})


class EditSortView(View):
    def post(self, request):
        # 验证登录
        user = request.user
        if not user.is_authenticated():
            return JsonResponse({'code': 0, 'errmsg': '用户未登录'})

        # 获取数据
        sort_id = request.POST.get('sort_id')
        sort_name = request.POST.get('sort_name')
        sort_desc = request.POST.get('sort_desc')
        parent_id = request.POST.get('parent_id')

        # 数据校验
        if not all([sort_id, sort_name, parent_id, sort_desc]):
            return JsonResponse({'code': 1, 'errmsg': '数据不完整'})

        # 当前分类是否存在
        try:
            sort = Sort.objects.get(id=sort_id)
        except Sort.DoesNotExist:
            sort = None

        if sort is None:
            return JsonResponse({'code': 2, 'errmsg': '分类不存在'})

        # 父分类是否存在
        sort_parent = None
        if parent_id != '-1':
            try:
                sort_parent = Sort.objects.get(id=parent_id)
            except Sort.DoesNotExist:
                return JsonResponse({'code': 3, 'errmsg': '父级分类不存在'})

        # 分类名是否被占用
        try:
            Sort.objects.exclude(id=sort_id).get(name=sort_name)
        except Sort.DoesNotExist:
            name_exist = False
        else:
            name_exist = True

        if name_exist:
            return JsonResponse({'code': 4, 'errmsg': '分类名已存在'})

        # 业务处理: 更新分类
        try:
            sort.name = sort_name
            sort.desc = sort_desc
            sort.parent = sort_parent
            sort.save()
        except Exception as e:
            return JsonResponse({'code': 5, 'errmsg': '更新失败'})

        # 返回响应
        return JsonResponse({'code': 6, 'msg': '更新成功'})


class CenterTagView(View):
    '''用户中心-标签'''
    @superuser_require
    def get(self, request):
        context = create_context(request)

        context['active_sort'] = 'tag'
        context['page'] = 'center'

        return render(request, 'center_tag.html', context)


class DelTagView(View):
    '''删除标签'''
    def post(self, request):
        # 校验登录
        user = request.user
        if not user.is_authenticated():
            return JsonResponse({'code': 0, 'errmsg': '用户未登录'})

        # 接收数据
        tid = request.POST.get('tid')

        # 校验数据
        if not tid:
            return JsonResponse({'code': 1, 'errmsg': '无效的标签id'})

        try:
            tag = Tag.objects.get(id=tid)
        except Tag.DoesNotExist:
            return JsonResponse({'code': 2, 'errmsg': '标签不存在'})

        # 业务处理: 删除分类
        try:
            tag.delete()
        except Exception as e:
            return JsonResponse({'code': 3, 'errmsg': '标签删除失败'})

        # 返回响应
        return JsonResponse({'code': 4, 'msg': '删除成功'})


class CreateTagView(View):
    '''创建标签'''
    def post(self, request):
        # 验证登录
        user = request.user
        if not user.is_authenticated():
            return JsonResponse({'code': 0, 'errmsg': '用户未登录'})

        # 获取数据
        tag_name = request.POST.get('tag_name')
        tag_desc = request.POST.get('tag_desc')

        # 数据校验
        if not all([tag_name, tag_desc]):
            return JsonResponse({'code': 1, 'errmsg': '数据不完整'})

        # 当前标签是否存在
        try:
            is_exists = Tag.objects.get(name=tag_name)
        except Tag.DoesNotExist:
            is_exists = None

        if is_exists:
            return JsonResponse({'code': 2, 'errmsg': '标签已存在'})

        # 业务处理: 创建标签
        try:
            tag = Tag.objects.create(name=tag_name, desc=tag_desc)
        except Exception as e:
            return JsonResponse({'code': 4, 'errmsg': '创建标签失败'})

        # 返回响应
        return JsonResponse({'code': 5, 'msg': '创建成功', 'tid': tag.id})


class EditTagView(View):
    '''编辑标签'''
    def post(self, request):
        # 验证登录
        user = request.user
        if not user.is_authenticated():
            return JsonResponse({'code': 0, 'errmsg': '用户未登录'})

        # 获取数据
        tag_id = request.POST.get('tag_id')
        tag_name = request.POST.get('tag_name')
        tag_desc = request.POST.get('tag_desc')

        # 数据校验
        if not all([tag_id, tag_name, tag_desc]):
            return JsonResponse({'code': 1, 'errmsg': '数据不完整'})

        # 当前标签是否存在
        try:
            tag = Tag.objects.get(id=tag_id)
        except Tag.DoesNotExist:
            tag = None

        if tag is None:
            return JsonResponse({'code': 2, 'errmsg': '标签不存在'})

        # 标签名是否被占用
        try:
            Tag.objects.exclude(id=tag_id).get(name=tag_name)
        except Tag.DoesNotExist:
            name_exist = False
        else:
            name_exist = True

        if name_exist:
            return JsonResponse({'code': 3, 'errmsg': '标签名已存在'})

        # 业务处理: 更新分类
        try:
            tag.name = tag_name
            tag.desc = tag_desc
            tag.save()
        except Exception as e:
            return JsonResponse({'code': 4, 'errmsg': '更新失败'})

        # 返回响应
        return JsonResponse({'code': 5, 'msg': '更新成功'})


class CenterPromotion(View):
    '''轮播图视图'''
    @superuser_require
    def get(self, request):
        context = create_context(request)

        promotions = PromotionArticle.objects.all()

        context['promotions'] = promotions
        context['active_sort'] = 'promotion'
        context['articles'] = Article.objects.all()

        return render(request, 'center_promotion.html', context)


class DelPromotionView(View):
    '''删除轮播图'''
    def post(self, request):
        # 校验登录
        user = request.user
        if not user.is_authenticated():
            return JsonResponse({'code': 0, 'errmsg': '用户未登录'})

        # 接收数据
        pid = request.POST.get('pid')

        # 校验数据
        if not pid:
            return JsonResponse({'code': 1, 'errmsg': '无效的轮播图id'})

        try:
            promotion = PromotionArticle.objects.get(id=pid)
        except PromotionArticle.DoesNotExist:
            return JsonResponse({'code': 2, 'errmsg': '轮播图不存在'})

        # 业务处理: 删除分类
        try:
            promotion.delete()
        except Exception as e:
            return JsonResponse({'code': 3, 'errmsg': '轮播图删除失败'})

        # 返回响应
        return JsonResponse({'code': 4, 'msg': '删除成功'})


class CreatePromotionView(View):
    '''添加轮播图'''
    def post(self, request):
        # 校验登录
        user = request.user
        if not user.is_authenticated():
            return JsonResponse({'code':0, 'errmsg':'用户未登录'})

        # 获取数据
        file = request.FILES.get('pro_img')
        aid = request.POST.get('aid')
        index = request.POST.get('index')

        # 数据校验
        if not all([file, aid, index]):
            return JsonResponse({'code':1, 'errmsg':'数据不完整'})

        try:
            index = int(index)
        except Exception as e:
            index = 0

        try:
            aid = int(aid)
        except Exception as e:
            return JsonResponse({'code':2, 'errmsg': '无效的文章id'})

        try:
            article = Article.objects.get(id=aid)
        except Article.DoesNotExist:
            return JsonResponse({'code':3, 'errmsg':'文章不存在'})

        # 业务处理: 创建轮播图
        # 上传到fdfs
        try:
            # 创建实例对象
            client = Fdfs_client(settings.FDFS_CLIENT_CONFIG)

            # 上传文件
            result = client.upload_by_buffer(file.read())

            # 判断是否上传成功并存储存储标识
            if result.get('Status') != 'Upload successed.':
                return JsonResponse({'code':4, 'errmsg': '图片上传失败01'})

            filename = result.get('Remote file_id')
        except Exception as e:
            return JsonResponse({'code': 5, 'errmsg': '图片上传失败02'})

        # 创建轮播图记录
        try:
            PromotionArticle.objects.create(article=article, index=index, image=filename)
        except Exception as e:
            return JsonResponse({'code': 6, 'errmsg': '轮播图创建失败!'})

        # 返回响应
        return JsonResponse({'code':7, 'msg':'创建成功!'})


class EditPromotionView(View):
    '''编辑轮播图'''
    def post(self, request):
        # 校验登录
        user = request.user
        if not user.is_authenticated():
            return JsonResponse({'code':0, 'errmsg': '用户未登录'})

        # 获取数据
        pid = request.POST.get('pid')
        file = request.FILES.get('pro_img')
        aid = request.POST.get('aid')
        index = request.POST.get('index')

        # 数据校验
        if not all([pid, aid, index]):
            return JsonResponse({'code':1, 'errmsg': '数据不完整'})

        try:
            promotion = PromotionArticle.objects.get(id=pid)
        except PromotionArticle.DoesNotExist:
            return JsonResponse({'code':2, 'errmsg': '轮播图不存在'})

        try:
            index = int(index)
        except Exception as e:
            index = 0

        try:
            aid = int(aid)
        except Exception as e:
            return JsonResponse({'code': 3, 'errmsg': '无效的文章id'})

        try:
            article = Article.objects.get(id=aid)
        except Article.DoesNotExist:
            return JsonResponse({'code': 4, 'errmsg': '文章不存在'})

        # 业务处理: 更新轮播图
        if file:
            try:
                client = Fdfs_client(settings.FDFS_CLIENT_CONFIG)
                result = client.upload_by_buffer(file.read())
                if result.get('Status') != 'Upload successed.':
                    return JsonResponse({'code':5, 'errmsg': '图片上传失败01'})

                filename = result.get('Remote file_id')
            except Exception as e:
                return JsonResponse({'code':6, 'errmsg': '图片上传失败02'})

            promotion.image = filename
        promotion.article = article
        promotion.index = index
        promotion.save()

        # 返回响应
        return JsonResponse({'code':7, 'msg': '更新成功'})


class ArticleUpView(View):
    '''点赞视图类'''
    def post(self, request):
        # 获取数据
        user = request.user
        aid = request.POST.get('aid')
        up_down_type = request.POST.get('up_down_type')

        # 校验数据
        if not all([aid, up_down_type]):
            return JsonResponse({'code':0, 'errmsg': '数据不完整'})

        try:
            article = Article.objects.get(id=aid)
        except Article.DoesNotExist:
            return JsonResponse({'code':1, 'errmsg': '无效的文章id'})

        # 业务处理: 点赞, 点踩
        try:
            up_down = ArticleUp.objects.get(user=user, article=article)
        except ArticleUp.DoesNotExist:
            # 未点过赞/踩
            if up_down_type == 'up':
                try:
                    ArticleUp.objects.create(up_or_down=1, user=user, article=article)
                    article.up_num += 1
                    article.save()
                except Exception as e:
                    pass
                return JsonResponse({'code':2, 'type': 'up'})
            else:
                ArticleUp.objects.create(up_or_down=0, user=user, article=article)
                return JsonResponse({'code':3, 'type': 'down'})
        else:
            # 已点过赞/踩
            up_down.delete()
            if up_down_type == 'up':
                article.up_num -= 1
                if article.up_num < 0:
                    article.up_num = 0
                article.save()
            return JsonResponse({'code':4, 'type': 'cancel'})


class FileUploadView(View):
    '''图片存储类'''
    def post(self, request):
        try:
            file = request.FILES.get('editormd-image-file')
        except Exception as e:
            print(e)
            result = {
                'success': 0,
                'message': '图片获取失败'
            }
            return JsonResponse(result)

        try:
            client = Fdfs_client(settings.FDFS_CLIENT_CONFIG)
            result = client.upload_by_buffer(file.read())
            if result.get('Status') != 'Upload successed.':
                result = {
                    'success': 0,
                    'message':'图片上传失败01'
                }
                return JsonResponse(result)

            filename = result.get('Remote file_id')
        except Exception as e:
            result = {
                'success': 0,
                'message': '图片上传失败02'
            }
            return JsonResponse(result)

        result = {
            'success': 1,
            'message': '上传成功',
            'url': settings.FDFS_SERVER_URL+filename
        }

        return JsonResponse(result)
