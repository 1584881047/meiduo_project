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



def get_goods_and_spec(sku_id,request):
    try:
        sku = SKU.objects.get(id=sku_id)
        sku.images =  sku.skuimage_set.all()
    except:
        return render(request, '404.html')

    goods = sku.goods


    # 获取当前产品的规格
    # sku_specs = SKUSpecification.objects.filter(sku = sku).order_by('spec_id')
    # [SKUSpecification(id=1),SKUSpecification(id =2)]
    sku_specs = sku.skuspecification_set.order_by('spec_id')


    sku_key = []

    for spec in sku_specs:
        sku_key.append(spec.option.id)
    #     [SpecificationOption.id,SpecificationOption.id...]

    spec_sku_map = {}
    skus = goods.sku_set.filter(is_launched = True)

    for sku in skus:
        # 每一个产品的规格
        s_specs = sku.skuspecification_set.order_by('spec_id')

        key = []
        for spec in s_specs:
            key.append(spec.option.id)


        spec_sku_map[tuple(key)] = sku.id

    goods_specs = goods.goodsspecification_set.order_by('id')

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














