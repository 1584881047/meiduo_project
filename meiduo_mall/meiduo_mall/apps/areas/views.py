from django import http
from django.core.cache import cache
from django.http import JsonResponse
from django.shortcuts import render

# Create your views here.
from django.views import View

from areas.models import Area
from meiduo_mall.utils.response_code import RETCODE


class SubAreasView(View):
    def get(self, request, pk):
        sub_data = cache.get('sub_data_%s' % pk)
        if not sub_data:
            try:
                parent_model = Area.objects.get(pk=pk)
                sub_model_list = Area.objects.filter(parent=pk)
                sub_list = []
                for sub_model in sub_model_list:
                    sub_list.append({'id': sub_model.id,
                                     'name': sub_model.name})
                    sub_data = {
                        'id': pk,
                        'name': parent_model.name,
                        'subs': sub_list
                    }
            except Exception as e:
                return http.JsonResponse({'code': RETCODE.DBERR,
                                          'errmsg': '城市或区县数据错误'})

        cache.set('sub_data_%s' % pk, sub_data, 3600)

        return http.JsonResponse({'code': RETCODE.OK,
                                  'errmsg': 'OK',
                                  'sub_data': sub_data})


class ProvinceAreasView(View):
    def get(self, request):

        province_list = cache.get('province_list') or []
        if province_list:
            return JsonResponse({'code': RETCODE.OK,
                                 'errmsg': 'OK',
                                 'province_list': province_list})

        try:
            province_model_list = Area.objects.filter(parent__isnull=True)
            for province_model in province_model_list:
                province_list.append({
                    'id': province_model.id,
                    'name': province_model.name
                })
        except Exception as e:
            return JsonResponse({'code': RETCODE.DBERR,
                                 'errmsg': '省份数据错误'})

        cache.set('province_list', province_list, 3600)
        return JsonResponse({'code': RETCODE.OK,
                             'errmsg': 'OK',
                             'province_list': province_list})
