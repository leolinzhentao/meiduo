from django.shortcuts import render
from rest_framework.views import APIView
import pickle, base64
from rest_framework.response import Response
from rest_framework import status
from django_redis import get_redis_connection

# Create your views here.

from .serializers import CartSerializer, CartSKUSerializer, CartDeleteSerializer, CartSelectedSerializer
from goods.models import SKU


class CartView(APIView):
    """购物车视图"""

    def perform_authentication(self, request):
        """因为前端js已做用户认证, 所以重写用户验证方法, 不在进入视图前就检查JWT"""
        pass

    def post(self, request):
        """添加购物车"""
        serializer = CartSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        sku_id = serializer.validated_data.get('sku_id')
        count = serializer.validated_data.get('count')
        selected = serializer.validated_data.get('selected')

        # 创建响应对象
        response = Response(serializer.data, status=status.HTTP_201_CREATED)

        try:
            user = request.user  # 接收登录用户, 首次获取会进行验证；如果代码可以往下执行说明是登录用户, 记录存储到redis

            # 创建redis连接对象
            redis_coun = get_redis_connection('cart')
            pl = redis_coun.pipeline()
            pl.hincrby('cart_%d' % user.id, sku_id, count)
            if selected:  # 判断当前商品是否勾选,把勾选的商品sku_id添加到set集合中
                pl.sadd('selected_%d' % user.id, sku_id)
            pl.execute()

        except:
        #     user = None
        #
        # # 判断用户是否登录
        # if user is not None and user.is_authenticated:
        #     # 用户已登录,操作redis购物车
        #     pass
        # else:
        #     # 用户未登录,操作cookie购物车
            # 获取cookie中的购物车数据
            cart_cookie = request.COOKIES.get('cart')

            # 判断是否有购物车数据
            if cart_cookie:
                # 把字符串转成python中的字典
                # 把字符串转成python字典
                cart_cookie_bytes = cart_cookie.encode()

                #把bytes类型的字符串转成bytes类型ascii码
                cart_ascii_bytes = base64.b64decode(cart_cookie_bytes)

                # 把bytes类型ascii码转成python中的字典
                cart_dict = pickle.loads(cart_ascii_bytes)

            else:
                # 之前没有cookie购物车数据
                cart_dict = {}

            # 判断本次添加的商品是否在购物车中已存在,如果已存在就做增量计算
            if sku_id in cart_dict:
                origin_count = cart_dict[sku_id]['count']
                count += origin_count

            cart_dict[sku_id] = {
                'count': count,
                'selected': selected
            }

            # 把python字典转成字符串
            cart_ascii_bytes = pickle.dumps(cart_dict)
            cart_cookie_bytes = base64.b64encode(cart_ascii_bytes)
            cart_str = cart_cookie_bytes.decode()

            response.set_cookie('cart', cart_str)

        return response

    def get(self, request):
        """查询购物车"""
        try:
            user = request.user  # 如果获取到user, 说明已登录(获取redis数据库)

        except:
            # 如果获取user异常,说明未登录(获取cookie购物车数据)
            user = None
        else:
            # 创建redis连接对象
            redis_coun = get_redis_connection('cart')
            # 获取hash数据
            cart_redis_dict = redis_coun.hgetall('cart_%d' % user.id)
            # 获取set数据
            selected_ids = redis_coun.smembers('selected_%d' % user.id)
            # 把redis的购物车数据转成与cookie购物车数据格式一样
            # 定义一个转换数据格式的大字典
            cart_dict = {}
            for sku_id_bytes in cart_redis_dict:
                cart_dict[int(sku_id_bytes)] = {
                    'count': int(cart_redis_dict[sku_id_bytes]),
                    'selected': sku_id_bytes in selected_ids
                }

        if not user:
            # 如果没有获取到user说明当前是未登录状态(cookie购物车信息)
            cart_str = request.COOKIES.get('cart')
            # 判断是否有cookie购物车数据
            if cart_str:
                cart_dict = pickle.loads(base64.b64decode(cart_str.encode()))

            else:
                cart_dict = {}
        # 以下序列化的代码无论登录还是未登录都要执行
        # 获取购物车中所有商品的sku数据
        skus = SKU.objects.filter(id__in=cart_dict.keys())

        # 遍历skus查询集,给里面的每个sku模型追加两个属性
        for sku in skus:
            sku.count = cart_dict[sku.id]['count']
            sku.selected = cart_dict[sku.id]['selected']

        # 创建序列化器进行序列化操作
        serializer = CartSKUSerializer(skus, many=True)

        return Response(serializer.data)

    def put(self, request):
        """修改购物车"""
        serializer = CartSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        sku_id = serializer.validated_data.get('sku_id')
        count = serializer.validated_data.get('count')
        selected = serializer.validated_data.get('selected')

        response = Response(serializer.data)

        try:
            user = request.user
        except:
            user = None
        else:
            # 已登录用户修改购物车数据(redis)
            redis_coun = get_redis_connection('cart')
            pl = redis_coun.pipeline()
            # 创建redis连接对象 hash字典
            # 勾选状态, set集合存储
            # 修改指定sku_id的购买数据, 把hash字典中的指定sku_id的value覆盖掉
            pl.hset('cart_%d' % user.id, sku_id, count)
            # 修改商品的勾选状态
            if selected:
                pl.sadd('selected_%d' % user.id, sku_id)

            else:
                pl.srem('selected_%d' % user.id, sku_id)

            pl.execute()

        if not user:
            # 未登录用户修改购物车数据(cookie)
            cart_str = request.COOKIES.get('cart')
            if cart_str:
                cart_dict = pickle.loads(base64.b64decode(cart_str.encode()))

                if sku_id in cart_dict:
                    # 直接覆盖商品的数量与勾选状态
                    cart_dict[sku_id] = {
                        'count': count,
                        'selected': selected
                    }

                cart_str = base64.b64encode(pickle.dumps(cart_dict)).decode()
                response.set_cookie('cart', cart_str)
        return response

    def delete(self, request):
        """删除购物车"""
        serializer = CartDeleteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        sku_id = serializer.validated_data.get('sku_id')

        response = Response(status=status.HTTP_204_NO_CONTENT)

        try:
            user = request.user
        except:
            user = None
        else:
            # 已登录用户操作redis购物车数据
            # 创建redis连接对象
            redis_coun = get_redis_connection('cart')
            pl = redis_coun.pipeline()
            # 把本次要删除的sku_id从hash字典中移除
            pl.hdel('cart_%d' % user.id, sku_id)
            # 把本次要删除的sku_id从set集合中移除
            pl.srem('selected_%d' % user.id, sku_id)
            pl.execute()

        if not user:
            # 未登录用户操作cookie购物车数据
            # 获取cookie数据
            cart_str = request.COOKIES.get('cart')
            # 把cart_str转成cart_dict
            if cart_str:
                cart_dict = pickle.loads(base64.b64decode(cart_str.encode()))
            # 把要删除的sku_id从cart_dict字典中删除
                if sku_id in cart_dict:
                    del cart_dict[sku_id]
                if len(cart_dict.keys()):
                    # rcn cart_dict转成cart_str
                    cart_str = base64.b64encode(pickle.dumps(cart_dict)).decode()
                    # 设置 cookie
                    response.set_cookie('cart', cart_str)
                else:
                    response.delete_cookie('cart')
        return response


class CartSelectedView(APIView):
    """购物车全选"""

    def perform_authentication(self, request):
        """因为前端js已做用户认证, 所以重写用户验证方法, 不在进入视图前就检查JWT"""
        pass

    def put(self, request):
        # 创建序列化器进行掇序列化
        serializer = CartSelectedSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        selected = serializer.validated_data.get('selected')

        response = Response(serializer.data)

        try:
            user = request.user
        except:
            user = None
        else:
            # 登录用户操作redis
            # 创建redis连接对象
            redis_coun = get_redis_connection('cart')
            # 获取到redis中的hash字典
            cart_redis_dict = redis_coun.hgetall('cart_%d' % user.id)
            # 判断是全选还是取消全选
            if selected:
                # 如果是全选,把所有sku_id全部添加到set中
                redis_coun.sadd('selected_%d' % user.id,*cart_redis_dict.keys())
                # 如果是取消全选,把set清空
            else:
                redis_coun.srem('selected_%d' % user.id,*cart_redis_dict.keys())

        if not user:
            # 未登录用户操作cookie
            # 获取cookie数据
            cart_str = request.COOKIES.get('cart')

            if cart_str:
                # 把cart_str转成cart_dict
                cart_dict = pickle.loads(base64.b64decode(cart_str.encode()))

                # 获取购物车中所有sku_id小字典
                for sku_id in cart_dict:
                    # 如果是全选, 把所有的selected改为True否则改为False
                    sku_id_dict = cart_dict[sku_id]
                    sku_id_dict['selected'] = selected

                    # 设置cookie
                cart_str = base64.b64encode(pickle.dumps(cart_dict)).decode()

                response.set_cookie('cart', cart_str)
        return response





