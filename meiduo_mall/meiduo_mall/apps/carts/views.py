import json

from django.shortcuts import render

# Create your views here.
from django import http
from django.views import View
from django_redis import get_redis_connection

from goods.models import SKU


class CartsView(View):
    def post(self,request):
        request_data= json.loads(request.body.decode())
        sku_id = request_data.get('sku_id')
        count = request_data.get('count')
        selected = request_data.get('selected')


        if not all([sku_id,count]):
            return http.HttpResponseForbidden('缺少必传参数')

        try:
            SKU.objects.get(id = sku_id)
        except SKU.DoesNotExist as e:
            return http.HttpResponseForbidden('商品不存在')

        try:
            count = int(count)
        except BaseException as e:
            return http.HttpResponseForbidden('参数count有误')

        # 判断selected是否为bool值
        if selected:
            if not isinstance(selected, bool):
                return http.HttpResponseForbidden('参数selected有误')

        cart = {
            'sku_id':sku_id,
            'count':count,
            'selected':{
                'is_select_%s'  % sku_id:  True,
            }
        }
        if request.user.is_authenticated:
            # 登录用户
            redis_conn = get_redis_connection('carts')
            pl = redis_conn.pipeline()


            pass
        else:
            # 未登录
            pass



