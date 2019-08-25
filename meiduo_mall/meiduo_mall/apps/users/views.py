import json
import re

from django import http
from django.contrib.auth import login, authenticate, logout
from django.db import DatabaseError
from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect

# Create your views here.
from django.urls import reverse
from django.views.generic.base import View
from django_redis import get_redis_connection

from celery_tasks.email.tasks import send_verify_email
from meiduo_mall.utils.response_code import RETCODE
from users.models import User, Address
from users.utils import LoginRequiredMixin


class UpdateTitleAddressView(View):
    def put(self, request, address_id):
        new_title = json.loads(request.body.decode()).get('title')
        if not new_title:
            return http.JsonResponse({'code': RETCODE.THROTTLINGERR,
                                      'errmsg': '缺少必传参数'})

        try:
            address = Address.objects.get(id=address_id)
            address.title = new_title
            address.save()
        except Exception as e:
            return http.JsonResponse({'code': RETCODE.DBERR, 'errmsg': '设置地址标题失败'})

        return http.JsonResponse({'code': RETCODE.OK, 'errmsg': '设置地址标题成功'})


class DefaultAddressView(View):
    def put(self, request, address_id):
        try:
            # address = Address.objects.get(id = address_id)
            request.user.default_address_id = address_id
            request.user.save()

        except BaseException as e:
            return http.JsonResponse({'code': RETCODE.DBERR, 'errmsg': '设置默认地址失败'})

        return http.JsonResponse({'code': RETCODE.OK, 'errmsg': '设置默认地址成功'})


class UpdateDestroyAddressView(View):
    def put(self, request, address_id):
        json_dict = json.loads(request.body.decode())
        receiver = json_dict.get('receiver')
        province_id = json_dict.get('province_id')
        city_id = json_dict.get('city_id')
        district_id = json_dict.get('district_id')
        place = json_dict.get('place')
        mobile = json_dict.get('mobile')
        tel = json_dict.get('tel')
        email = json_dict.get('email')

        if not all([receiver, province_id, city_id, district_id, place, mobile]):
            return http.HttpResponseForbidden('缺少必传参数')
        if not re.match(r'^1[3-9]\d{9}$', mobile):
            return http.HttpResponseForbidden('参数mobile有误')
        if tel:
            if not re.match(r'^(0[0-9]{2,3}-)?([2-9][0-9]{6,7})+(-[0-9]{1,4})?$', tel):
                return http.HttpResponseForbidden('参数tel有误')
        if email:
            if not re.match(r'^[a-z0-9][\w\.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$', email):
                return http.HttpResponseForbidden('参数email有误')

            try:
                # result 是uodate返回更新的条数
                #          create 返回的创建的实列对象

                result = Address.objects.filter(id=address_id).update(
                    user=request.user,
                    title=receiver,
                    receiver=receiver,
                    province_id=province_id,
                    city_id=city_id,
                    district_id=district_id,
                    place=place,
                    mobile=mobile,
                    tel=tel,
                    email=email
                )
            except BaseException as e:
                return http.JsonResponse({'code': RETCODE.DBERR,
                                          'errmsg': '更新地址失败'})

            address = Address.objects.get(id=address_id)
            address_dict = {
                "id": address.id,
                "title": address.title,
                "receiver": address.receiver,
                "province": address.province.name,
                "city": address.city.name,
                "district": address.district.name,
                "place": address.place,
                "mobile": address.mobile,
                "tel": address.tel,
                "email": address.email
            }

            return http.JsonResponse({'code': RETCODE.OK,
                                      'errmsg': '更新地址成功',
                                      'address': address_dict})

    def delete(self, request, address_id):
        try:
            # update 一定要是查询集调用filter(),查询对象不能调用 get()
            Address.objects.filter(id=address_id).update(is_deleted=True)
        except BaseException as e:
            return http.JsonResponse({'code': RETCODE.DBERR, 'errmsg': '删除地址失败'})

        return http.JsonResponse({'code': RETCODE.OK, 'errmsg': '删除地址成功'})


class CreateAddressView(View):
    def post(self, request):
        # 极值判断
        # count = request.user.address_set.filter(is_deleted=False).count()
        count = Address.objects.filter(Q(user=request.user) & Q(is_deleted=False)).count()
        # count = request.user.addresses.filter(is_deleted=False).count()
        print(count)
        if count >= 20:
            return http.JsonResponse({'code': RETCODE.THROTTLINGERR,
                                      'errmsg': '超过地址数量上限'})

        json_dict = json.loads(request.body.decode())
        receiver = json_dict.get('receiver')
        province_id = json_dict.get('province_id')
        city_id = json_dict.get('city_id')
        district_id = json_dict.get('district_id')
        place = json_dict.get('place')
        mobile = json_dict.get('mobile')
        tel = json_dict.get('tel')
        email = json_dict.get('email')

        if not all([receiver, province_id, city_id, district_id, place, mobile]):
            return http.JsonResponse({'code': RETCODE.THROTTLINGERR,
                                      'errmsg': '缺少必传参数'})

        if not re.match(r'^1[3-9]\d{9}$', mobile):
            return http.HttpResponseForbidden('参数mobile有误')
        if tel:
            if not re.match(r'^(0[0-9]{2,3}-)?([2-9][0-9]{6,7})+(-[0-9]{1,4})?$', tel):
                return http.HttpResponseForbidden('参数tel有误')
        if email:
            if not re.match(r'^[a-z0-9][\w\.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$', email):
                return http.HttpResponseForbidden('参数email有误')

        try:
            address = Address.objects.create(
                user=request.user,
                title=receiver,
                receiver=receiver,
                province_id=province_id,
                city_id=city_id,
                district_id=district_id,
                place=place,
                mobile=mobile,
                tel=tel,
                email=email
            )

            if not request.user.default_address:
                request.user.default_address = address
                request.user.save()
        except Exception as e:
            return http.JsonResponse({'code': RETCODE.DBERR, 'errmsg': '新增地址失败'})

        address_dict = {
            "id": address.id,
            "title": address.title,
            "receiver": address.receiver,
            "province": address.province.name,
            "city": address.city.name,
            "district": address.district.name,
            "place": address.place,
            "mobile": address.mobile,
            "tel": address.tel,
            "email": address.email
        }

        return http.JsonResponse({'code': RETCODE.OK,
                                  'errmsg': '新增地址成功',
                                  'address': address_dict})


class AddressView(LoginRequiredMixin, View):
    """用户收货地址"""

    def get(self, request):
        """提供收货地址界面"""
        """提供地址管理界面
          """
        # 获取所有的地址:
        addresses = Address.objects.filter(user=request.user, is_deleted=False)

        # 创建空的列表
        address_dict_list = []
        # 遍历
        for address in addresses:
            address_dict = {
                "id": address.id,
                "title": address.title,
                "receiver": address.receiver,
                "province": address.province.name,
                "city": address.city.name,
                "district": address.district.name,
                "place": address.place,
                "mobile": address.mobile,
                "tel": address.tel,
                "email": address.email
            }

            # 将默认地址移动到最前面
            if request.user.default_address.id == address.id:
                # 查询集 addresses 没有 insert 方法
                address_dict_list.insert(0, address_dict)
            else:
                address_dict_list.append(address_dict)

        context = {
            'default_address_id': request.user.default_address_id,
            'addresses': address_dict_list,
            'username': request.user.username,
        }

        return render(request, 'user_center_site.html', context)


class VerifyEmailView(View):
    def get(self, request):
        token = request.GET.get('token')

        if not token:
            return http.HttpResponseBadRequest('缺少token')

        user = User.check_verify_email_token(token)

        if not user:
            return http.HttpResponseForbidden('无效的token')

        try:
            user.email_active = True
            user.save()
        except BaseException:
            return http.HttpResponseServerError('激活邮件失败')

        # 返回邮箱验证结果
        return redirect(reverse('users:info'))


class EmailView(LoginRequiredMixin, View):
    def put(self, request):
        email = json.loads(request.body.decode()).get('email')
        if not email:
            return http.HttpResponseForbidden('邮箱地址不能为空')

        if not re.match(r'^[a-z0-9][\w\.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$', email):
            return http.HttpResponseForbidden('邮箱格式不正确')

        try:
            request.user.email = email
            request.user.save()
        except BaseException as e:
            print(e)
            return http.JsonResponse({'code': RETCODE.DBERR, 'errmsg': '添加邮箱失败'})

        # TODO 发送验证邮箱 在celery 异步处理
        # 生成验证URL
        verify_url = request.user.generate_verify_email_url()

        send_verify_email.delay(email, verify_url)

        return http.JsonResponse({'code': RETCODE.OK, 'errmsg': '添加邮箱成功'})


class UserInfoView(LoginRequiredMixin, View):
    def get(self, request):
        return render(request, 'user_center_info.html', {
            'username': request.user.username,
            'mobile': request.user.mobile,
            'email': request.user.email,
            'email_active': request.user.email_active
        })


class LogoutView(View):

    def get(self, request):
        logout(request)
        response = redirect(reverse('contents:index'))
        response.delete_cookie('username')
        return response


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
        # 重定向到要跳转的页面
        next = request.GET.get('next')
        if not next:
            return redirect(reverse('contents:index'))
        else:
            return redirect(next)


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
        # 保存用户名草cookie
        response = redirect(reverse('contents:index'))
        response.set_cookie('username', user.username, max_age=3600 * 24 * 7)
        # 重定向到首页
        return response


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
