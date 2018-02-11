from django.conf.urls import url
from . import views
urlpatterns = [
    url(r'^register$', views.Register.as_view(), name='register'),
    url(r'^login$', views.Longin.as_view(), name='login'),
    url(r'^logout$', views.Logout.as_view(), name='logout'),
    url(r'^send_active_email$', views.send_active_email, name='send_active_email'),
    url(r'^active/(?P<token>.+)$', views.Active.as_view(), name='active'),
    url(r'^user_center_site$', views.UserCenterSite.as_view(), name='user_center_site'),
    url(r'^user_center_info$', views.UserCenterInfo.as_view(), name='user_center_info'),
    url(r'^user_center_order$', views.UserCenterOrder.as_view(), name='user_center_order'),
]