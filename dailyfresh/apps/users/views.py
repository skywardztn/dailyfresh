from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.core.urlresolvers import reverse
from django.db.backends.mysql.base import IntegrityError
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.views.generic import View
from django_redis import get_redis_connection

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
    return render(request, 'apps/login.html', {'user_error': '邮件已发送,请登陆注册邮箱查看'})
    # return redirect(reverse('users:login'), {'user_error': '邮件已发送,请登陆注册邮箱查看'})


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
        if not all([username, pwd]):
            return render(request, 'apps/login.html', {'user_error': '请输入用户名和密码'})

        user = authenticate(username=username, password=pwd)
        # 判断是否存在用户
        if user is None:
            return render(request, 'apps/login.html', {'user_error': '用户名不存在'})
        if user.is_active is False:
            token = user.generate_active_token()[0]
            user_email = user.generate_active_token()[1]
            context = {
                'link': '账户未激活,点击激活',
                'to_email': user_email,
                'user_name': username,
                'token': token
            }
            return render(request, 'apps/login.html', context)
        # return redirect(reverse('user:user_center_site'))
        login(request, user)
        if remember != '1':
            # 没有勾选，不需要记住cookie信息，浏览会话结束后过期
            request.session.set_expiry(0)
        else:
            # 已勾选，需要记住cookie信息，两周后过期
            request.session.set_expiry(None)
        return redirect(reverse('users:user_center_site'))


# 登出
class Logout(View):
    def get(self, request):
        logout(request)
        # return redirect(reverse('goods:index'))
        return render(request, 'apps/user_center_site.html')


class LoginRequired(View):
  """验证用户是否登陆"""
  @classmethod
  def as_view(cls, **initkwargs):
      view = super().as_view()
      return login_required(view)


# 用户中心
class UserCenterSite(LoginRequired):
    def get(self, request):
        user = request.user
        try:
            # 查询用户地址：根据创建时间排序，最近的时间在最前，取第1个地址
            # addr = Address.objects.filter(user=user).order_by('-create_time')
            addr = user.address_set.latest('create_time')
        except Address.DoesNotExist:
            addr = None
        context = {
            'addr': addr
        }
        return render(request, 'apps/user_center_site.html', context)

    def post(self, request):
        posts = request.POST
        user = request.user
        receiver_name = posts['receiver_name']
        receiver_mobile = posts['receiver_mobile']
        detail_addr = posts['detail_addr']
        zip_code = posts['zip_code']
        if all([receiver_name, receiver_mobile, detail_addr, zip_code]):
            Address.objects.create(
                user=user,
                receiver_name=receiver_name,
                receiver_mobile=receiver_mobile,
                detail_addr=detail_addr,
                zip_code=zip_code
            )
            return redirect(reverse('users:user_center_site'))


class UserCenterInfo(LoginRequired):
    def get(self, request):
        user = request.user
        try:
            # 查询用户地址：根据创建时间排序，最近的时间在最前，取第1个地址
            # addr = Address.objects.filter(user=user).order_by('-create_time')
            addr = user.address_set.latest('create_time')
        except Address.DoesNotExist:
            addr = None
        # 创建redis连接对象
        redis_connection = get_redis_connection('default')
        # 从Redis中获取用户浏览商品的sku_id，在redis中需要维护商品浏览顺序[8,2,5]
        sku_ids = redis_connection.lrange('history_%s' % user.id, 0, 4)

        # 从数据库中查询商品sku信息,范围在sku_ids中
        # skuList = GoodsSKU.objects.filter(id__in=sku_ids)
        # 问题：经过数据库查询后得到的skuList，就不再是redis中维护的顺序了,而是[2,5,8]
        # 需求：保证经过数据库查询后，依然是[8,2,5]
        skuList = []
        for sku_id in sku_ids:
            sku = GoodsSKU.objects.get(id=sku_id)
            skuList.append(sku)
        context = {
            'addr': addr,
            'skuList': skuList
        }

        return render(request, 'apps/user_center_info.html', context)


class UserCenterOrder(LoginRequired):
    def get(self, request):
        return render(request, 'apps/user_center_order.html')