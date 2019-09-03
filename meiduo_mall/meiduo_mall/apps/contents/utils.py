from collections import OrderedDict

from django.shortcuts import render

from goods.models import GoodsChannel, SKU


def get_categories():
    # 定义一个有序字典对象
    categories = OrderedDict()
    # 对 GoodsChannel 进行 group_id 和 sequence 排序, 获取排序后的结果:
    channels = GoodsChannel.objects.order_by('group_id', 'sequence')
    for channel in channels:
        group_id = channel.group_id
        if group_id not in categories:
            categories[group_id] = {
                'channels': [],
                'sub_cats': []
            }
        cat1 = channel.category
        categories[group_id]['channels'].append({
            'id': cat1.id,
            'name': cat1.name,
            'url': '/static/images/assv%02d.jpg' %cat1.id
        })
        # 找到cat1 下面所有的 cat2
        for cat2 in cat1.goodscategory_set.all():
            cat2.sub_cats = []
            for cat3 in cat2.goodscategory_set.all():
                cat2.sub_cats.append(cat3)
            categories[group_id]['sub_cats'].append(cat2)

    return categories




def get_breadcrumb(category):
    # 定义一个字典:
    breadcrumb = dict(
        cat1='',
        cat2='',
        cat3=''
    )
    if category.parent is None:
        # 当前类别为一级类别
        breadcrumb['cat1'] = category
    elif category.goodscategory_set.count() == 0:
        # 当前类别为三级
        breadcrumb['cat3'] = category
        cat2 = category.parent
        breadcrumb['cat2'] = cat2
        breadcrumb['cat1'] = cat2.parent
    else:
        # 当前类别为二级
        breadcrumb['cat2'] = category
        breadcrumb['cat1'] = category.parent

    return breadcrumb



def get_goods_and_spec(sku_id, request):
    # 获取当前sku的信息
    try:
        sku = SKU.objects.get(id=sku_id)
        sku.images = sku.skuimage_set.all()
    except SKU.DoesNotExist:
        return render(request, '404.html')

    # 面包屑导航信息中的频道
    goods = sku.goods
    # goods.channel = goods.category1.goodschannel_set.all()[0]

    # 构建当前商品的规格键
    # sku_key = [规格1参数id， 规格2参数id， 规格3参数id, ...]
    sku_specs = sku.skuspecification_set.order_by('spec_id')
    # sku_specs = sku.specs.order_by('spec_id')
    sku_key = []
    for spec in sku_specs:
        sku_key.append(spec.option.id)

    # 获取当前商品的所有SKU
    skus = goods.sku_set.all()

    # 构建不同规格参数（选项）的sku字典
    # spec_sku_map = {
    #     (规格1参数id, 规格2参数id, 规格3参数id, ...): sku_id,
    #     (规格1参数id, 规格2参数id, 规格3参数id, ...): sku_id,
    #     ...
    # }
    spec_sku_map = {}
    for s in skus:
        # 获取sku的规格参数
        s_specs = s.skuspecification_set.order_by('spec_id')
        # s_specs = s.specs.order_by('spec_id')
        # 用于形成规格参数-sku字典的键
        key = []
        for spec in s_specs:
            key.append(spec.option.id)
        # 向规格参数-sku字典添加记录
        spec_sku_map[tuple(key)] = s.id

    # 获取当前商品的规格信息
    # specs = [
    #    {
    #        'name': '屏幕尺寸',
    #        'options': [
    #            {'value': '13.3寸', 'sku_id': xxx},
    #            {'value': '15.4寸', 'sku_id': xxx},
    #        ]
    #    },
    #    {
    #        'name': '颜色',
    #        'options': [
    #            {'value': '银色', 'sku_id': xxx},
    #            {'value': '黑色', 'sku_id': xxx}
    #        ]
    #    },
    #    ...
    # ]
    goods_specs = goods.goodsspecification_set.order_by('id')
    # goods_specs = goods.specs.order_by('id')
    # 若当前sku的规格信息不完整，则不再继续
    if len(sku_key) < len(goods_specs):
        return
    for index, spec in enumerate(goods_specs):
        # 复制当前sku的规格键
        key = sku_key[:]
        # 该规格的选项
        spec_options = spec.specificationoption_set.all()
        # spec_options = spec.options.all()
        for option in spec_options:
            # 在规格参数sku字典中查找符合当前规格的sku
            key[index] = option.id
            option.sku_id = spec_sku_map.get(tuple(key))

        # spec.options = spec_options
        spec.spec_options = spec_options

    data = {
        'goods':goods,
        'goods_specs':goods_specs,
        'sku':sku
    }

    return data














