
from django.shortcuts import render, redirect

# Create your views here.
from django.urls import reverse
from django.views.generic.base import View

from contents.models import ContentCategory
from contents.utils import get_categories


class IndexView(View):

    def get(self, request):
        """
        获取首页模板
        :param request:
        :return:
        """
        categories = get_categories()
        dict = {}

        # 查询出所有的广告类别
        content_categories = ContentCategory.objects.all()
        # 遍历所有的广告类别, 然后放入到定义的空字典中:
        for cat in content_categories:
            # 获取类别所对应的展示数据, 并对数据进行排序:
            # key:value  ==>  商品类别.key:具体的所有商品(排过序)
            dict[cat.key] = cat.content_set.filter(status=True).order_by('sequence')

        context = {
            # 这是首页需要的一二级分类信息:
            'categories': categories,
            # 这是首页需要的能展示的三级信息:
            'contents': dict,
        }

        return render(request, 'index.html',context=context)




