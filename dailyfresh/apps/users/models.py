from django.db import models
from django.contrib.auth.models import AbstractUser
from utils.models import BaseModel
from django.conf import settings
from goods.models import GoodsSKU
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer


class User(AbstractUser, BaseModel):
    class Meta:
        db_table = "df_users"
        verbose_name = "用户"  # admin站点使用
        verbose_name_plural = verbose_name

    def generate_active_token(self):
        """生成激活令牌"""
        serializer = Serializer(settings.SECRET_KEY, 3600)
        token = serializer.dumps({"confirm": self.id})  # 返回bytes类型
        to_email = serializer.dumps({'gakafo': self.email})
        return token.decode(),to_email.decode()


class Address(BaseModel):
    """地址"""
    user = models.ForeignKey(User, verbose_name="所属用户")
    receiver_name = models.CharField(max_length=20, verbose_name="收件人")
    receiver_mobile = models.CharField(max_length=11, verbose_name="联系电话")
    detail_addr = models.CharField(max_length=256, verbose_name="详细地址")
    zip_code = models.CharField(max_length=6, verbose_name="邮政编码")

    class Meta:
        db_table = "df_address"
        verbose_name = "用户地址"  # admin站点使用
        verbose_name_plural = verbose_name
