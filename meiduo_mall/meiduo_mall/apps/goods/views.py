import json
from datetime import datetime

from django import http
from django.core.paginator import Paginator, EmptyPage
from django.shortcuts import render

# Create your views here.
from django.utils import timezone
from django.views import View
from django_redis import get_redis_connection

from contents.utils import get_categories, get_breadcrumb, get_goods_and_spec
from goods.models import GoodsCategory, SKU, GoodsVisitCount
from meiduo_mall.utils.response_code import RETCODE


class ListView(View):
    def get(self, request, category_id, page_num):
        try:
            # 获取分组
            category = GoodsCategory.objects.get(id=category_id)
        except GoodsCategory.DoesNotExist:
            return http.HttpResponseNotFound('GoodsCategory 不存在')

        # 查询商品频道分类
        categories = get_categories()

        breadcrumb = get_breadcrumb(category)

        # 获取排序规则
        sort = request.GET.get('sort', 'default')
        # 按照排序规则查询该分类商品SKU信息
        if sort == 'price':
            # 按照价格由低到高
            sortkind = 'price'
        elif sort == 'hot':
            # 按照销量由高到低
            sortkind = '-sales'
        else:
            # 'price'和'sales'以外的所有排序方式都归为'default'
            sort = 'default'
            sortkind = 'create_time'
            # 获取当前分类并且上架的商品.( 并且对商品按照排序字段进行排序 )
        skus = SKU.objects.filter(category=category,
                                  is_launched=True).order_by(sortkind)

        # 创建分页器：每页N条记录
        # # 列表页每页商品数据量
        # GOODS_LIST_LIMIT = 5
        paginator = Paginator(skus, 5)
        # 获取每页商品数据
        try:
            page_skus = paginator.page(page_num)
        except EmptyPage:
            # 如果page_num不正确，默认给用户404
            return http.HttpResponseNotFound('empty page')
        # 获取列表页总页数
        total_page = paginator.num_pages

        # 渲染页面
        context = {
            'categories': categories,  # 频道分类
            'breadcrumb': breadcrumb,  # 面包屑导航
            'sort': sort,  # 排序字段
            'category': category,  # 第三级分类
            'page_skus': page_skus,  # 分页后数据
            'total_page': total_page,  # 总页数
            'page_num': page_num,  # 当前页码
        }
        return render(request, 'list.html', context)


class HotGoodsView(View):
    def get(self, request, category_id):
        skus = SKU.objects.filter(category_id=category_id,
                                  is_launched=True).order_by('-sales')[:2]
        hot_skus = []
        for sku in skus:
            hot_skus.append({
                'id': sku.id,
                'default_image_url': sku.default_image_url,
                'name': sku.name,
                'price': sku.price
            })

        return http.JsonResponse({'code': RETCODE.OK, 'errmsg': 'OK', 'hot_skus': hot_skus})


class DetailView(View):
    def get(self, request, sku_id):
        data = get_goods_and_spec(sku_id, request)

        # 商品分类菜单
        categories = get_categories()

        # 获取面包屑导航:
        breadcrumb = get_breadcrumb(data['goods'].category3)

        context = {
            'categories': categories,
            'goods': data.get('goods'),
            'specs': data.get('goods_specs'),
            'sku': data.get('sku'),
            'breadcrumb': breadcrumb
        }

        return render(request, 'detail.html', context)


class DetailVisitView(View):
    def post(self, request, category_id):
        try:
            category = GoodsCategory.objects.get(id=category_id)
        except:
            return http.HttpResponseForbidden('缺少必传参数')

        t = timezone.localtime()
        today_str = '%d-%02d-%02d' % (t.year, t.month, t.day)
        today_data = datetime.strptime(today_str, '%Y-%m-%d')

        try:
            obj = GoodsVisitCount.objects.get(category_id=category_id, date=today_data)

        except:
            obj = GoodsVisitCount()
            obj.category = category

        try:
            obj.count += 1
            obj.save()
        except:
            return http.HttpResponseServerError('服务器异常')

        return http.JsonResponse({'code': RETCODE.OK, 'errmsg': 'OK'})


class UserBrowseHistory(View):
    def post(self,request,):
        sku_id =  json.loads(request.body.decode()).get('sku_id')

        try:
            SKU.objects.get(id = sku_id)
        except SKU.DoesNotExist as e:
            return http.HttpResponseForbidden('sku不存在')


        redis_conn = get_redis_connection('history')
        pl = redis_conn.pipeline()
        user_id = request.user.id

        # 从左开始删除所有sku_id
        pl.lrem('history_%s' % user_id,0,sku_id)

        pl.lpush('history_%s' % user_id, sku_id)
        # 最后截取: 界面有限, 只保留 5 个
        pl.ltrim('history_%s' % user_id, 0, 4)
        pl.execute()

        return http.JsonResponse({'code': RETCODE.OK, 'errmsg': 'OK'})


    def get(self,request):
        user_id = request.user.id

        redis_conn = get_redis_connection('history')
        sku_ids = redis_conn.lrange('history_%s' % user_id,0,-1)

        skus = []
        for sku_id in sku_ids:
            sku = SKU.objects.get(id = sku_id )
            skus.append({
                'id':sku.id,
                "name": sku.name,
                "default_image_url": sku.default_image_url,
                "price": sku.price
            })
        return http.JsonResponse({'code': RETCODE.OK, 'errmsg': 'OK', 'skus': skus})










