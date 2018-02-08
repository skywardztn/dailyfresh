from django.core.urlresolvers import reverse
from django.shortcuts import render, redirect
from . import models
from hashlib import sha1


def register(request):
    return render(request, 'register.html')


def handle_user(request):
    if request.method == 'POST':
        post = request.POST
        user_name = post['user_name']
        pwd  = post['pwd']
        cpwd = post['cpwd']
        email = post['email']
        allow = post.get('allow', 0)
        if allow != '1':
            return redirect(reverse('users:register'))
        else:
            if pwd == cpwd:
                jiami = sha1()
                jiami.update(pwd.encode())
                pwd = jiami.hexdigest()
                user = models.User()
                user.username = user_name
                user.password = pwd
                user.email = email
                user.save()
                return redirect(reverse('users:login'))
    else:
        return redirect(reverse('users:register'))


def login(request):
    return render(request, 'login.html')