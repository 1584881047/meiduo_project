from django.db import models

# Create your models here.
from meiduo_mall.utils.models import BaseModel


class OAuthQQUser(BaseModel):
    user = models.ForeignKey('users.User',  on_delete=models.CASCADE,verbose_name='用户信息')
    openId = models.CharField(max_length=64,db_index=True,verbose_name='openId')
    class Meta:
        db_table = 'tb_oauth_qq'
        verbose_name = 'QQ登录用户数据'
        verbose_name_plural = verbose_name
