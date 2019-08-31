import base64
import datetime
import pickle

from django_redis import get_redis_connection




# def merge_cart_cookie_to_redis(request,response):
#     def out_func(func):
#         def inner_func(*args,**kwargs):
#             cookie_dict = request.COOKIES.get('carts')
#             if cookie_dict:
#                 carts_dict = pickle.loads(base64.b64decode(cookie_dict))
#                 new_dict = {}
#                 new_add = []
#                 new_remove = []
#                 for sku_id, item in carts_dict.items():
#                     new_dict[sku_id] = item['count']
#                     if item['selected']:
#                         new_add.append(sku_id)
#                     else:
#                         new_remove.append(sku_id)
#
#                 redis_conn = get_redis_connection('carts')
#                 pl = redis_conn.pipeline()
#
#                 pl.hmset('carts_%s' % request.user.id, new_dict)
#                 if new_add:
#                     pl.sadd('selected_%s' % request.user.id, *new_add)
#                 if new_remove:
#                     pl.srem('selected_%s' % request.user.id, *new_remove)
#
#                 pl.execute()
#                 response.delete_cookie('carts')
#             else:
#                 func(*args, **kwargs)
#
#         return inner_func
#     return out_func


def merge_cart_cookie_to_redis(request,response):
    cookie_dict = request.COOKIES.get('carts')
    if cookie_dict:
        carts_dict = pickle.loads(base64.b64decode(cookie_dict))

        new_dict = {}
        new_add = []
        new_remove = []
        for sku_id,item in carts_dict.items():
            new_dict[sku_id] = item['count']
            if item['selected']:
                new_add.append(sku_id)
            else:
                new_remove.append(sku_id)

        redis_conn = get_redis_connection('carts')
        pl = redis_conn.pipeline()

        pl.hmset('carts_%s' % request.user.id,new_dict)
        if new_add:
            pl.sadd('selected_%s' % request.user.id, *new_add)
        if new_remove:
            pl.srem('selected_%s' % request.user.id, *new_remove)

        pl.execute()
        response.set_cookie('carts',expires = datetime.datetime(1999, 5, 28, 23, 44, 55))
        # response.set_cookie('carts',max_age = -1)
        # response.delete_cookie('carts')


    return response

