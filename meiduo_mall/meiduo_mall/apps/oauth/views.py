import re

from QQLoginTool.QQtool import OAuthQQ
from django import http
from django.contrib.auth import login
from django.shortcuts import render, redirect
from django.conf import settings
from django_redis import get_redis_connection

# Create your views here.
from django.urls import reverse
from django.views import View
from itsdangerous import TimedJSONWebSignatureSerializer

from meiduo_mall.utils.response_code import RETCODE
from oauth.models import OAuthQQUser
from oauth.utils import MD5
from users.models import User


class QQURLView(View):
    def get(self, request):
        """
        获取QQ登录地址
        :param request:
        :return:
        """
        next = request.GET.get('next')
        auth = OAuthQQ(
            client_id=settings.QQ_CLIENT_ID,
            client_secret=settings.QQ_CLIENT_SECRET,
            redirect_uri=settings.QQ_REDIRECT_URI,
            state=next
        )
        try:
            login_url = auth.get_qq_url()
        except:
            return http.HttpResponseForbidden('链接QQ服务器异常')
        return http.JsonResponse({'code': RETCODE.OK, 'errmsg': 'OK', 'login_url': login_url})


class QQUserView(View):
    def get(self, request):
        code = request.GET.get('code')
        if code is None:
            return http.HttpResponseForbidden('必传参数不能为空')

        # 根据code 获取access_token

        auth = OAuthQQ(
            client_id=settings.QQ_CLIENT_ID,
            client_secret=settings.QQ_CLIENT_SECRET,
            redirect_uri=settings.QQ_REDIRECT_URI,
        )
        try:
            access_token = auth.get_access_token(code)
            # 根据access_token 获取openid
            openid = auth.get_open_id(access_token)
        except:
            return http.HttpResponseForbidden('获取openid失败')

        try:
            user = OAuthQQUser.objects.get(openId=openid)
        except BaseException as e:
            # 用户首次用QQ 登录
            access_token = MD5(openid).generate_access_token()
            context = {'access_token': access_token}
            return render(request, 'oauth_callback.html', context)
        else:
            # 用户非首次QQ登录
            # 1 状态保持
            login(request, user.user)
            response = redirect(reverse('contents:index'))
            response.set_cookie('username', user.user.username, max_age=3600 * 24 * 7)
            return response

    def post(self, request):
        mobile = request.POST.get('mobile')
        password = request.POST.get('password')
        sms_code_cli = request.POST.get('sms_code')
        access_token = request.POST.get('access_token')

        if not all([mobile, password, sms_code_cli]):
            return http.HttpResponseForbidden('必传参数不能为空')
            # 判断手机号是否合法
        if not re.match(r'^1[3-9]\d{9}$', mobile):
            return http.HttpResponseForbidden('请输入正确的手机号码')

        # 判断密码是否合格
        if not re.match(r'^[0-9A-Za-z]{8,20}$', password):
            return http.HttpResponseForbidden('请输入8-20位的密码')

        # 判断短信验证码
        redis_conn = get_redis_connection('verify_code')

        sms_code_ser = redis_conn.get('sms_code_%s' % mobile)

        if sms_code_ser is None:
            return render(request, 'oauth_callback.html', {'sms_code_errmsg': '无效的短信验证码'})

        if sms_code_cli != sms_code_ser.decode():
            return render(request, 'oauth_callback.html', {'sms_code_errmsg': '输入短信验证码有误'})


        openid = MD5(access_token).check_access_token()

        if not openid:
            return render(request, 'oauth_callback.html', {'openid_errmsg': '无效的openid'})


        try:
            user = User.objects.get(mobile=mobile)
            if OAuthQQUser.objects.filter(user=user).count() > 0 :
                return render(request, 'oauth_callback.html', {'account_errmsg': '此用户已经绑定过QQ'})

        except:
            # 用户不存在,新建
            user = User.objects.create_user(username=mobile,password=password,mobile=mobile)
        else:
            # 用户存在检验密码
            if not user.check_password(password):
                return render(request, 'oauth_callback.html', {'account_errmsg': '用户名或密码错误'})

        # 将用户存入表中
        try:
            OAuthQQUser.objects.create(openId=openid,user=user)
        except:
            return render(request, 'oauth_callback.html', {'qq_login_errmsg': 'QQ登录失败'})


        login(request,user)

        # 7.响应绑定结果
        next = request.GET.get('state')
        response = redirect(next)

        response.set_cookie('username', user.username, max_age=3600 * 24 * 15)

        # 9.响应
        return response


