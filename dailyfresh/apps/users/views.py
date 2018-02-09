from django.contrib.auth import login, authenticate, logout
from django.core.mail import send_mail
from django.core.urlresolvers import reverse
from django.db.backends.mysql.base import IntegrityError
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.views.generic import View
from .models import *
from django.conf import settings
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer, SignatureExpired
from celery_tasks.tasks import send_active_emails


# 发送邮件
def send_active_email(request):
    to_email = request.GET.get('em')
    serializer = Serializer(settings.SECRET_KEY, 3600)
    try:
        # 使用序列化器，获取token明文信息,需要判断签名是否过期
        result = serializer.loads(to_email)
    except SignatureExpired:
        # 提示激活链接已过期
        return HttpResponse('激活链接已过期')
    to_email = result.get('gakafo')
    user_name = request.GET.get('um')
    token = request.GET.get('tk')
    send_active_emails.delay(to_email, user_name, token)
    return redirect(reverse('users:login'))


# 激活账户
class Active(View):
    def get(self, request, token):
        serializer = Serializer(settings.SECRET_KEY, 3600)
        try:
            # 使用序列化器，获取token明文信息,需要判断签名是否过期
            result = serializer.loads(token)
        except SignatureExpired:
            return HttpResponse('激活链接已过期')
        # 获取对应的id
        user_id = result.get('confirm')

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return HttpResponse('用户不存在')

        user.is_active = True
        user.save()
        return redirect(reverse('users:login'))


# 注册
class Register(View):
    def get(self, request):
        context = {
            'title': '天天生鲜-注册'
        }
        return render(request, 'apps/register.html', context)

    def post(self, request):
        post = request.POST
        user_name = post['user_name']
        pwd = post['pwd']
        cpwd = post['cpwd']
        email = post['email']
        allow = post.get('allow', 0)

        # 用户输入判断是否为空
        if not all([user_name, pwd, cpwd, email]):
            return render(request, 'apps/register.html', {'data': '你的输入有误', 'username': user_name, 'email': email})
        # 判断两次输入是否一致
        if pwd != cpwd:
            return render(request, 'apps/register.html', {'data': '密码不一致', 'username': user_name, 'email': email})
        # 判断是否勾选协议
        if allow != '1':
            return render(request, 'apps/register.html', {'data': '请勾选协议', 'username': user_name, 'email': email})
        # 以上条件都符合,创建用户,并判断是否存在此用户
        try:
            user = User.objects.create_user(user_name, email, pwd)
            # 修改默认的用户激活状态为False
            user.is_active = False
            user.save()
            # return redirect(reverse('users:login'))
            token = user.generate_active_token()[0]
            user_email = user.generate_active_token()[1]
            context = {
                'link': '注册成功,请点击激活',
                'to_email': user_email,
                'user_name': user_name,
                'token': token
            }
            return render(request, 'apps/register.html', context)
        except IntegrityError:
            return render(request, 'apps/register.html', {'data': '用户已被注册', 'username': user_name, 'email': email})


# 登录
class Longin(View):
    def get(self, request):
        context = {
            'title': '天天生鲜-登录'
        }
        return render(request, 'apps/login.html', context)

    def post(self, request):
        post = request.POST
        username = post['username']
        pwd = post['pwd']
        remember = post.get('remember', 0)
        # print(remember)
        if username and pwd:
            user = authenticate(username=username, password=pwd)
            if user is not None:
                login(request, user)
                # 判断是否是否勾选'记住用户名'
                if remember != '1':
                    request.session.set_expiry(0)
                else:
                    request.session.set_expiry(None)
                return redirect(reverse('users:user_center_site'))
                # return render(request, 'user_center_site.html')
            else:
                return render(request, 'apps/login.html', {'tip': 'block'})
        else:
            return render(request, 'apps/login.html', {'tip': 'block'})


# 登出
class Logout(View):
    def get(self, request):
        logout(request)
        # return redirect(reverse('goods:index'))
        return render(request, 'apps/user_center_site.html')


# 用户中心
class UserCenterSite(View):
    def get(self, request, response):
        print(response.status_code)
        if response.status_code == '302':
            return render(request, 'apps/user_center_site.html', {'none': 'none','block': 'block'})
        else:
            return HttpResponse('error')