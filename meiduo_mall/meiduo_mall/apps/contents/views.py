
from django.shortcuts import render, redirect

# Create your views here.
from django.urls import reverse
from django.views.generic.base import View


class IndexView(View):

    def get(self, request):
        """
        获取首页模板
        :param request:
        :return:
        """
        return render(request, 'index.html')


