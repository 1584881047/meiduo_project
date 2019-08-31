import base64
import json
import pickle

from django.shortcuts import render

# Create your views here.
from django import http
from django.views import View
from django_redis import get_redis_connection

from goods.models import SKU
from meiduo_mall.utils.response_code import RETCODE


class CartsView(View):
    def post(self, request):
        request_data = json.loads(request.body.decode())
        sku_id = request_data.get('sku_id')
        count = request_data.get('count')
        selected = request_data.get('selected', True)

        if not all([sku_id, count]):
            return http.HttpResponseForbidden('缺少必传参数')

        try:
            SKU.objects.get(id=sku_id)
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

        if request.user.is_authenticated:
            # 登录用户
            redis_conn = get_redis_connection('carts')
            pl = redis_conn.pipeline()

            # 追加数量
            pl.hincrby('carts_%s' % request.user.id, sku_id, count),
            # 选中状态添加商品id
            if selected:
                pl.sadd('selected_%s' % request.user.id, sku_id)

            pl.execute()

            return http.JsonResponse({'code': RETCODE.OK,
                                      'errmsg': '添加购物车成功'})
        else:
            # 未登录
            carts_dict = request.COOKIES.get('carts')

            if carts_dict:
                # 有值
                carts_dict = pickle.loads(base64.b64decode(carts_dict))
            else:
                # 无值
                carts_dict = {}

            if sku_id in carts_dict:
                count += carts_dict[sku_id]['count']

            carts_dict[sku_id] = {
                'count': count,
                'selected': selected
            }

            carts_dict = base64.b64encode(pickle.dumps(carts_dict)).decode()

            response = http.JsonResponse({'code': RETCODE.OK,
                                          'errmsg': '添加购物车成功'})

            response.set_cookie('carts', carts_dict)
            return response

    def get(self, request):
        user = request.user

        if user.is_authenticated:
            # 登录
            redis_conn = get_redis_connection('carts')
            item_dict = redis_conn.hgetall('carts_%s' % user.id)
            cart_selected = redis_conn.smembers('selected_%s' % user.id)
            # key == sku_id
            # value = {count:count}
            cart_dict = {}
            for (key, value) in item_dict.items():
                cart_dict[int(key)] = {
                    'count': int(value),
                    'selected': key in cart_selected
                }

        else:
            # 未登录
            cart_dict = request.COOKIES.get('carts')
            if cart_dict:
                cart_dict = pickle.loads(base64.b64decode(cart_dict))
            else:
                cart_dict = {}

        skus_id = cart_dict.keys()
        try:
            skus = SKU.objects.filter(id__in=skus_id)
        except BaseException as e:
            response = http.JsonResponse({'code': RETCODE.DBERR,
                                          'errmsg': '添加购物车失败'})

        cart_skus = []
        for sku in skus:
            cart_skus.append({
                'id': sku.id,
                'name': sku.name,
                'count': cart_dict.get(sku.id).get('count'),
                'selected': str(cart_dict.get(sku.id).get('selected')),  # 将True，转'True'，方便json解析
                'default_image_url': sku.default_image_url,
                'price': str(sku.price),  # 从Decimal('10.2')中取出'10.2'，方便json解析
                'amount': str(sku.price * cart_dict.get(sku.id).get('count')),
            })

        context = {
            'cart_skus': cart_skus,
        }

        # 渲染购物车页面
        return render(request, 'cart.html', context)

    def put(self, request):
        request_data = json.loads(request.body.decode())
        sku_id = request_data.get('sku_id')
        count = request_data.get('count')
        selected = request_data.get('selected')

        if not all([sku_id, count]):
            return http.HttpResponseForbidden('缺少必传参数')

        try:
            sku = SKU.objects.get(id=sku_id)
        except SKU.DoesNotExist:
            return http.HttpResponseForbidden('商品sku_id不存在')

        try:
            count = int(count)
        except BaseException as e:
            return http.HttpResponseForbidden('参数count有误')

        if selected:
            if not isinstance(selected, bool):
                return http.HttpResponseForbidden('参数selected有误')

        cart_sku = {
            'id': sku_id,
            'count': count,
            'selected': selected,
            'name': sku.name,
            'default_image_url': sku.default_image_url,
            'price': sku.price,
            'amount': sku.price * count,
        }
        response = http.JsonResponse({'code': RETCODE.OK,
                                      'errmsg': '修改购物车成功',
                                      'cart_sku': cart_sku})
        # 判断用户是否登录
        if request.user.is_authenticated:
            # 登录  操作redis
            redis_conn = get_redis_connection('carts')
            pl = redis_conn.pipeline()

            pl.hset('carts_%s' % request.user.id, sku_id, count)
            if selected:
                pl.sadd('selected_%s' % request.user.id, sku_id)
            else:
                pl.srem('selected_%s' % request.user.id, sku_id)

            pl.execute()

        else:
            # 未登录 操作cookies
            cookie_dict = request.COOKIES.get('carts')
            carts_dict = {}
            if cookie_dict:
                carts_dict = pickle.loads(base64.b64decode(cookie_dict))

            if carts_dict:
                carts_dict[sku_id] = {
                    'count': count,
                    'selected': selected
                }
            carts_dict = base64.b64encode(pickle.dumps(carts_dict)).decode()

            # 响应结果并将购物车数据写入到cookie
            response.set_cookie('carts', carts_dict)

        return response

    def delete(self, request):
        sku_id = json.loads(request.body.decode()).get('sku_id')

        try:
            sku = SKU.objects.get(id=sku_id)
        except SKU.DoesNotExist:
            return http.HttpResponseForbidden('商品sku_id不存在')

        response = http.JsonResponse({'code': RETCODE.OK,
                                      'errmsg': '删除购物车成功'})

        if request.user.is_authenticated:
            redis_conn = get_redis_connection('carts')
            pl = redis_conn.pipeline()

            pl.hdel('carts_%s' % request.user.id, sku_id)
            pl.srem('selected_%s' % request.user.id, sku_id)
            pl.execute()
        else:

            cookie_dict = request.COOKIES.get('carts')
            if cookie_dict:
                carts_dict = pickle.loads(base64.b64decode(cookie_dict))
                if sku_id in carts_dict:
                    del carts_dict[sku_id]

                carts_dict = base64.b64encode(pickle.dumps(carts_dict)).decode()

                response.set_cookie('carts', carts_dict)

        return response


class CartSelectAllView(View):
    def put(self, request):
        selected = json.loads(request.body.decode()).get('selected')

        if selected:
            if not isinstance(selected, bool):
                return http.HttpResponseForbidden('参数selected有误')

        response = http.JsonResponse({'code': RETCODE.OK,
                                      'errmsg': '全选购物车成功'})

        if request.user.is_authenticated:
            # 登录状态  操作redis
            redis_conn = get_redis_connection('carts')
            pl = redis_conn.pipeline()

            carts_dict = redis_conn.hgetall('carts_%s' % request.user.id)
            skus_id = carts_dict.keys()

            if selected:
                pl.sadd('selected_%s' % request.user.id, *skus_id)
            else:
                pl.srem('selected_%s' % request.user.id, *skus_id)

            pl.execute()

        else:
            # 未登录  操作cookies
            cookie_dict = request.COOKIES.get('carts')

            if cookie_dict:
                carts_dict = pickle.loads(base64.b64decode(cookie_dict))
                for sku_id, item in carts_dict.items():
                    item['selected'] = selected

                cart_data = base64.b64encode(pickle.dumps(carts_dict)).decode()
                response.set_cookie('carts', cart_data)

        return response
