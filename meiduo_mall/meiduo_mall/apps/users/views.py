import json
import re

from django import http
from django.contrib.auth import login, authenticate
from django.db import DatabaseError
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect

# Create your views here.
from django.urls import reverse
from django.views.generic.base import View
from django_redis import get_redis_connection

from users.models import User


class LoginView(View):
    def get(self, request):
        return render(request, 'login.html')

    def post(self, request):
        # 获取参数
        username = request.POST.get('username')
        password = request.POST.get('password')
        remembered = request.POST.get('remembered')

        # 非空校验
        if not all([username, password]):
            return http.HttpResponseForbidden('缺少必传参数')
        # 判断格式
        if not re.match(r'^[a-zA-Z0-9_-]{5,20}$', username):
            return http.HttpResponseForbidden('用户名格式不正确')

        if not re.match(r'^[a-zA-Z0-9_-]{8,20}$', password):
            return http.HttpResponseForbidden('密码格式不正确')

        # 判断登录 重写authenticate在utils
        user = authenticate(username=username, password=password)

        if user is None:
            return render(request, 'login.html', {'account_errmsg': '用户名或密码错误'})

        # 判断是否记住账号
        if remembered == 'on':
            # 记住账号
            request.session.set_expiry(None)
        else:
            request.session.set_expiry(0)

        # 状态保持
        login(request, user)
        # 保存到cookie 用户名
        response = redirect(reverse('contents:index'))
        response.set_cookie('username', user.username, max_age=3600 * 24 * 7)
        # 重定向到首页
        return redirect(reverse('contents:index'))


class RegisterView(View):
    """用户注册"""

    def get(self, request):
        """
        提供注册界面
        :param request: 请求对象
        :return: 注册界面
        """
        return render(request, 'register.html')

    def post(self, request):
        """
        注册用户
        :param request: 请求对象
        :return:
        """
        username = request.POST.get('username')
        password = request.POST.get('password')
        password2 = request.POST.get('password2')
        mobile = request.POST.get('phone')
        allow = request.POST.get('allow')
        # TODO 短信验证
        sms_code_cli = request.POST.get('msg_code')

        # 非空校验
        if not all([username, password, password2, mobile, allow, sms_code_cli]):
            return http.HttpResponseForbidden('必传参数不能为空')
        # 参数校验
        if not re.match(r'^[a-zA-Z0-9_-]{5,20}$', username):
            return http.HttpResponseForbidden('请输入5-20个字符的用户名')
        if not re.match(r'^[0-9A-Za-z]{8,20}$', password):
            return http.HttpResponseForbidden('请输入8-20位的密码')
        if password != password2:
            return http.HttpResponseForbidden('两次输入的密码不一致')
        if not re.match(r'^1[345789]\d{9}$', mobile):
            return http.HttpResponseForbidden('手机号码格式不正确')
        if allow != 'on':
            return http.HttpResponseForbidden('请勾选用户协议')

        # 获取短信验证码
        redis_conn = get_redis_connection('verify_code')
        sms_code_ser = redis_conn.get('sms_code_%s' % mobile).decode()
        if sms_code_ser != sms_code_cli:
            return http.HttpResponseForbidden('短信验证码有误')

        # 保存数据库
        try:
            user = User.objects.create_user(username=username, password=password, mobile=mobile)
        except DatabaseError:
            return render(request, 'register.html', {'register_errmsg': '注册失败'})
        # 会话保持
        login(request, user)
        # 重定向到首页
        return redirect(reverse('contents:index'))


class UsernameCountView(View):

    def get(self, request, username):
        print('用户校验')
        """
        判断用户名是否重复
        :param request:  请求对象
        :param username: 用户姓名
        :return:  用户名在数据库的个数
        """

        count = User.objects.filter(username=username).count()
        return JsonResponse({'code': '0000', 'errmsg': 'ok', 'count': count})


class MobileCountView(View):

    def get(self, request, mobile):
        print('手机号校验')
        """
        判断手机号是否重复
        :param request: 请求对象
        :param mobile: 手机号
        :return: 手机号在数据库的个数
        """
        count = User.objects.filter(mobile=mobile).count()
        return JsonResponse({'code': '0000', 'errmsg': 'ok', 'count': count})
