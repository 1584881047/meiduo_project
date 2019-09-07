import json
from _decimal import Decimal

from django import http
from django.core.paginator import Paginator, EmptyPage
from django.db import transaction
from django.db.models import Q
from django.shortcuts import render

# Create your views here.
from django.utils import timezone
from django.views import View
from django_redis import get_redis_connection

from goods.models import SKU
from meiduo_mall.utils.response_code import RETCODE
from orders.models import OrderInfo, OrderGoods
from users.models import Address
from users.utils import LoginRequiredMixin


class OrderSettlementView(LoginRequiredMixin, View):
    def get(self, request):

        # 获取地址
        try:
            addresses = Address.objects.filter(Q(user=request.user) & Q(is_deleted=False))
        except Address.DoesNotExist as e:
            addresses = None

        # 获取购物车数据
        redis_conn = get_redis_connection('carts')
        h_dict = redis_conn.hgetall('carts_%s' % request.user.id)
        s_dict = redis_conn.smembers('selected_%s' % request.user.id)

        carts_dict = {}
        for sku_id in s_dict:
            carts_dict[int(sku_id)] = int(h_dict[sku_id])

        skus_id = carts_dict.keys()
        skus = SKU.objects.filter(id__in=skus_id)

        total_count = 0
        total_amount = Decimal(0.00)
        for sku in skus:
            sku.count = carts_dict[sku.id]
            sku.amount = carts_dict[sku.id] * sku.price
            total_count += sku.count
            total_amount += sku.amount

        # 补充运费
        freight = Decimal('10.00')

        # 渲染界面
        context = {
            'addresses': addresses,
            'skus': skus,
            'total_count': total_count,
            'total_amount': total_amount,
            'freight': freight,
            'payment_amount': total_amount + freight
        }

        return render(request, 'place_order.html', context)


class OrderCommitView(LoginRequiredMixin, View):
    def post(self, request):
        """
        :param request:
        :return:
        """
        request_data = json.loads(request.body.decode())
        address_id = request_data.get('address_id')
        pay_method = request_data.get('pay_method')

        if not all([address_id, pay_method]):
            return http.HttpResponseForbidden('缺少必传参数')

        try:
            address = Address.objects.get(id=address_id)
        except Address.DoesNotExist as e:
            return http.HttpResponseForbidden('参数address_id错误')

        if pay_method not in [OrderInfo.PAY_METHODS_ENUM['CASH'], OrderInfo.PAY_METHODS_ENUM['ALIPAY']]:
            return http.HttpResponseForbidden('参数pay_method错误')

            # 获取登录用户
        user = request.user
        # 生成订单编号：年月日时分秒+用户编号
        order_id = timezone.localtime().strftime('%Y%m%d%H%M%S') + ('%09d' % user.id)

        # 链接redis
        redis_conn = get_redis_connection('carts')
        h_dic = redis_conn.hgetall('carts_%s' % user.id)
        s_dic = redis_conn.smembers('selected_%s' % user.id)

        # 添加事物
        with transaction.atomic():
            # 创建保存点
            save_id = transaction.savepoint()

            try:
                order_info = OrderInfo.objects.create(
                    order_id=order_id,
                    user=user,
                    address=address,
                    total_count=0,
                    total_amount=Decimal('0'),
                    freight=Decimal('10.00'),
                    pay_method=pay_method,
                    status=pay_method == OrderInfo.PAY_METHODS_ENUM['CASH'] and OrderInfo.ORDER_STATUS_ENUM[
                        'UNSEND'] or OrderInfo.ORDER_STATUS_ENUM['UNPAID'],
                )

                for sku_id in s_dic:
                    sku = SKU.objects.get(id=sku_id)
                    #  购物车商品的个数
                    sku_count = int(h_dic[sku_id])
                    while True:
                        # 添加乐观锁逻辑
                        # 商品库存的个数 和 商品的销量数
                        origin_stock = sku.stock
                        origin_sales = sku.sales

                        if origin_stock < sku_count:
                            # 事物回滚
                            transaction.savepoint_rollback(save_id)
                            return http.JsonResponse({
                                'code': RETCODE.STOCKERR,
                                'errmsg': '库存不足'})

                        # 修改数据
                        # try:
                        #     obj = SKU.objects.get(id=sku.id,
                        #                           stock=origin_stock,
                        #                           sales=origin_sales
                        #                           )
                        # except SKU.DoesNotExist as e:
                        #     continue
                        #
                        # obj.stock -= sku_count
                        # obj.sales += sku_count
                        # obj.save()
                        # break

                        new_stock = origin_stock - sku_count
                        new_sales = origin_sales + sku_count
                        result = SKU.objects.filter(id=sku.id,
                                                    stock=origin_stock,
                                                    sales=origin_sales).update(
                                                    stock=new_stock, sales=new_sales
                                                    )
                        if result:
                            break
                        continue
                    sku.goods.sales += sku_count
                    sku.goods.save()
                    # 保存订单商品信息 OrderGoods（多）
                    OrderGoods.objects.create(
                        order=order_info,
                        sku=sku,
                        count=sku_count,
                        price=sku.price,
                    )

                    # 保存商品订单中总价和总数量
                    order_info.total_count += sku_count
                    order_info.total_amount += (sku_count * sku.price)

                order_info.total_amount += order_info.freight
                order_info.save()
            except BaseException as e:
                transaction.savepoint_rollback(save_id)
                print(e)
                return http.JsonResponse({
                    'code': RETCODE.DBERR,
                    'errmsg': '下单失败'})

            transaction.savepoint_commit(save_id)

        # 清空 已经下单的购物车
        redis_conn.srem('selected_%s' % user.id, *s_dic)
        redis_conn.hdel('carts_%s' % user.id, *s_dic)

        # 响应提交订单结果
        return http.JsonResponse({
            'code': RETCODE.OK,
            'errmsg': '下单成功',
            'order_id': order_info.order_id})


class OrderSuccessView(LoginRequiredMixin, View):
    """提交订单成功"""

    def get(self, request):
        order_id = request.GET.get('order_id')
        payment_amount = request.GET.get('payment_amount')
        pay_method = request.GET.get('pay_method')

        context = {
            'order_id': order_id,
            'payment_amount': payment_amount,
            'pay_method': pay_method
        }
        return render(request, 'order_success.html', context)



class UserOrderInfoView(LoginRequiredMixin,View):
    def get(self,request,page_num):
        user = request.user

        try:
            orders = user.orderinfo_set.all().order_by("-create_time")
        except BaseException as e:
            orders = []

        for order in orders :
            order_goods = order.skus.all()
            order.status_name =OrderInfo.ORDER_STATUS_CHOICES[order.status-1] [1]
            order.pay_method_name = OrderInfo.PAY_METHOD_CHOICES[order.pay_method - 1][1]
            order.sku_list = []

            for order_good in order_goods:
                sku = order_good.sku
                sku.count = order_good.count
                sku.amount = sku.count * sku.price
                order.sku_list.append(sku)


        # 分页
        try:
            paginator = Paginator(orders, 2)
            page_orders = paginator.page(page_num)
            total_page = paginator.num_pages
        except EmptyPage as e:
            return http.HttpResponseNotFound('订单不存在')

        context = {
            "page_orders": page_orders,
            'total_page': total_page,
            'page_num': page_num,
        }
        return render(request, "user_center_order.html", context)





