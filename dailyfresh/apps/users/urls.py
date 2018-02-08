from django.conf.urls import include, url
from . import views

urlpatterns = [
    url(r'^register$', views.register, name='register'),
    url(r'^handle_user$', views.handle_user, name='handle_user'),
    url(r'^login$', views.login, name='login')
]