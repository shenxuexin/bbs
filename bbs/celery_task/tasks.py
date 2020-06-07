from celery import Celery
from django.conf import settings
from django.core.mail import send_mail

# 启动django-读取settings
import os
import django
# 来源于 bbs.wsgi
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "bbs.settings")
django.setup()


# 创建实例对象
app = Celery('celery_tasks.tasks', broker='redis://192.168.153.131:6379/5')


# 注册任务
@app.task
def send_active_mail(email, token):
    active_url = 'http://192.168.153.131:8000/user/active/%s' % token

    subject = '个人博客-用户激活'
    msg = ''
    sender = settings.EMAIL_HOST_USER
    receiver = [email]
    html_msg = '<h1>欢迎关注我的个人博客</h1>请点击以下链接进行激活: <a href="%s">%s</a>' % (active_url, active_url)
    send_mail(subject, msg, sender, receiver, html_message=html_msg)