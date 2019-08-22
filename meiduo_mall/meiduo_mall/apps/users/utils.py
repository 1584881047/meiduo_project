import re

from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect

from users.models import User


# 多用户登录
class UsernameMobileAuthBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):

        user = self.get_user_by_account(username)
        if user and user.check_password(password):
            return user
        else:
            return None

    def get_user_by_account(self, account):
        try:
            if re.match(r'^1[3-9]\d{9}$', account):
                user = User.objects.get(mobile=account)
            else:
                user = User.objects.get(username=account)
        except BaseException as e:
            return None
        else:
            return user




def myLogin_required(func):
    def inner_func(request,*args, **kwargs):
        next = '/login/'+'?next='+request.path
        # 判断用户是否登录
        u = request.user.is_authenticated
        if u :
            return func(request, *args, **kwargs)
        else:
            print('未登录')

            return redirect(next)
    return inner_func


# 验证用户登录扩展类
class LoginRequiredMixin(object):
    @classmethod
    def as_view(cls, *args, **kwargs):
        view = super().as_view(*args, **kwargs)
        # 添加用户登录校验
        # return login_required(view)
        return myLogin_required(view)
