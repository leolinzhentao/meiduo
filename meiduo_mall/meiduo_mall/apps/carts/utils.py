"""购物车cookie合并到redis"""
import pickle, base64
from django_redis import get_redis_connection

def merge_cart_cookie_to_redis(request, user, response):
    """以cookie合并到redis"""
    # 获取cookie购物车数据
    cart_str = request.COOKIES.get('cart')
    # 判断,如果没有cookie购物车数据,以下代码不需要执行
    if cart_str is None:
        return

    # 把cart_str 转成cart_dict
    cookie_cart_dict = pickle.loads(base64.b64decode(cart_str.encode()))

    # 将redis和cookie两个购物车数据设置成同样格式
    # 定义一个中间合并字典
    # new_redis_cart_dict = {}
    # 获取出redis中的购物车数据, 并存入中间字典中
    redis_coun = get_redis_connection('cart')
    # 获取hash中的数据
    # redis_cart_dict = redis_coun.hgetall('cart_%d' % user.id)
    # 获取set中的数据
    # redis_selected_ids = redis_coun.smembers('selected_%d' % user.id)
    # 再把redis的购物车数据存入中间字典中
    # for sku_id_bytes in redis_cart_dict:
    #     new_redis_cart_dict[int(sku_id_bytes)] = {
    #         'count': int(redis_cart_dict[sku_id_bytes]),
    #         'selected': sku_id_bytes in redis_selected_ids
    #     }
    # 再把cookie的购物车数据也存入中间字典中
    # for sku_id in cookie_cart_dict:
    #     new_redis_cart_dict[sku_id] = {
    #         'count': cookie_cart_dict[sku_id]['count'],
    #         'selected': cookie_cart_dict[sku_id]['selected'] or sku_id.encode() in redis_selected_ids
    #     }
    # 把合并后的字典再分别设置到redis中
    # for sku_id, sku_id_dict in new_redis_cart_dict.items():
    #     redis_coun.hset('cart_%d' % user.id, sku_id, sku_id_dict['count'])
    #     if sku_id_dict['selected']:
    #         redis_coun.sadd('selected_%d' % user.id, sku_id)
    #
    # 遍历cookie字典 将sku_id和count直接加入到redis中, 如果cookie中的sku_id在hash中已存在, 会以cookie去覆盖hash
    for sku_id in cookie_cart_dict:
        redis_coun.hset('cart_%d' % user.id, sku_id, cookie_cart_dict[sku_id]['count'])
        if cookie_cart_dict[sku_id]['selected']:
            redis_coun.sadd('selected_%d' % user.id, sku_id)

    # 清空购物车
    response.delete_cookie('cart')
