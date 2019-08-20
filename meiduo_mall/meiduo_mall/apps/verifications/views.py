import random

from django.http import HttpResponse, JsonResponse
from django.shortcuts import render

# Create your views here.
from django.views.generic.base import View
from django_redis import get_redis_connection

from celery_tasks.sms.tasks import send_code
from meiduo_mall.libs.captcha.captcha import captcha
from meiduo_mall.libs.yuntongxun.ccp_sms import CCP
from meiduo_mall.utils import response_code


class SMSCodeView(View):
    def get(self, request, mobile):
        """
        校验图形验证码,并且发送短信
        :param request:
        :param SMSCodeView:
        :return:
        """
        # 获取参数
        image_code_cli = request.GET.get('image_code')
        uuid = request.GET.get('image_code_id')

        # 非空校验
        if not all([image_code_cli, image_code_cli]):
            return JsonResponse(
                {'code': response_code.RET.DATAERR, 'errmsg': '必传参数不能为空'})

        # 链接数据库
        redis_conn = get_redis_connection('verify_code')

        # 取出数据
        image_code_ser = redis_conn.get('img_%s' % uuid)

        # 校验数据
        if image_code_ser is None:
            return JsonResponse(
                {'code': response_code.RETCODE.IMAGECODEERR, 'errmsg': '图片验证码过时'})

        # 删除验证码
        try:
            redis_conn.delete('img_%s' % uuid)
        except BaseException as e:
            print(e)

        # 校验验证码
        if image_code_cli.lower() != image_code_ser.decode().lower():
            return JsonResponse(
                {'code': response_code.RETCODE.IMAGECODEERR, 'errmsg': '图形验证码不一致'})

        return self.send_sms_code(mobile)

    def send_sms_code(self, mobile):
        """
        发送验证码
        :param mobile: 手机号
        :return:
        """
        # 链接数据库
        redis_conn = get_redis_connection('verify_code')
        # 校验频繁发送
        send_flag= redis_conn.get('sms_flag_%s' % mobile)
        if send_flag:
            return JsonResponse(
                {'code': response_code.RETCODE.THROTTLINGERR, 'errmsg': '请勿频繁操作'})
        # 生成随机验证码
        sms_code = '%06d' % random.randint(0, 999999)
        print(sms_code)

        # 保存短信验证码
        pl = redis_conn.pipeline()
        pl.setex('sms_code_%s' % mobile, 300, sms_code)
        pl.setex('sms_flag_%s' % mobile, 60, 1)
        pl.execute()
        # 发送短信验证码
        send_code.delay(mobile,sms_code)
        # CCP().send_template_sms(mobile, [sms_code, '5'], 1)

        # TODO 发送短信 返回OK
        return JsonResponse(
            {'code': response_code.RETCODE.OK, 'errmsg': 'OK'})


class ImageCodeView(View):
    def get(self, request, uuid):
        """

        :param request:
        :param uuid: 唯一标识
        :return:  图片
        """
        # 获取图片验证码
        text, image = captcha.generate_captcha()
        # 链接django-redis 数据库
        redis_conn = get_redis_connection('verify_code')
        # 存入redis 数据
        redis_conn.setex('img_%s' % uuid, 300, text)

        return HttpResponse(image, content_type='imgae/jpg')
