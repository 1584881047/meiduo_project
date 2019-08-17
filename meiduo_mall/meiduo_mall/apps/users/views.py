from django.http import HttpResponse
from django.shortcuts import render

# Create your views here.
from django.views.generic.base import View


class RegisterView(View):
    def get(self, request):
        response = HttpResponse('RegisterView')
        response['Access-Control-Allow-Origin'] = '*'

        return response
