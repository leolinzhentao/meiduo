from decimal import Decimal
from django.utils import timezone
from django_redis import get_redis_connection
from django.db import transaction

from rest_framework import serializers

from goods.models import SKU
from .models import OrderInfo, OrderGoods


class CommitOrderSerializer(serializers.ModelSerializer):
    """保存订单序列化器"""
    # 订单基本事务, 要么一起成功, 要么一起失败

    class Meta:
        model = OrderInfo
        fields = ['order_id', 'pay_method', 'address']
        # order_id 只做输出, pay_method/address只做输入
        read_only_fields = ['order_id']
        extra_kwargs = {
            'address': {
                'write_only': True,
                'required': True,
            },
            'pay_method': {
                'write_only': True,
                'required': True
            }
        }

    def create(self, validated_data):
        """重写序列化器的create方法进行存储订单表/订单商品"""
        # 获取当前下单用户
        user = self.context['request'].user
        # 生成订单编号  当前时间 + user_id
        order_id = timezone.now().strftime('%Y%m%d%H%M%S') + '%09d' % user.id
        # 获取用户收货地址
        address = validated_data.get('address')
        # 获取用户付款方式
        pay_method = validated_data.get('pay_method')
        # 获取订单状态
        status = (OrderInfo.ORDER_STATUS_ENUM['UNPAID']
                  if OrderInfo.PAY_METHODS_ENUM['ALIPAY'] == pay_method
                  else OrderInfo.ORDER_STATUS_ENUM['UNSEND'])
        # 开启事务
        with transaction.atomic():
            # 创建事务保存点
            save_point = transaction.savepoint()
            try:
                # 保存订单基本信息数据 OrderInfo
                order = OrderInfo.objects.create(
                    order_id=order_id,
                    user=user,
                    address=address,
                    total_count=0,
                    total_amount=Decimal('0.00'),
                    freight=Decimal('10.00'),
                    pay_method=pay_method,
                    status=status,

                )
                # 从redis中获取购物车结算商品数据
                redis_coun = get_redis_connection('cart')
                cart_redis_dict = redis_coun.hgetall('cart_%d' % user.id)
                cart_selected_ids = redis_coun.smembers('selected_%d' % user.id)

                cart_selected_dict = {}
                for sku_id_bytes in cart_selected_ids:
                    cart_selected_dict[int(sku_id_bytes)] = int(cart_redis_dict[sku_id_bytes])

                # 遍历结算商品：
                # skus = SKU.objects.filter(id__in=cart_selected_dict.keys())
                for sku_id in cart_selected_dict:

                    while True:
                        # 获取sku对象
                        sku = SKU.objects.get(id=sku_id)
                        # 获取当前sku_id商品需购买的数量
                        sku_count = cart_selected_dict[sku_id]

                        # 获取查询出sku_id时的库存和销量
                        origin_stock = sku.stock
                        origin_sales = sku.sales

                        # 判断商品库存是否充足
                        if sku_count > origin_stock:
                            raise serializers.ValidationError('库存不足')
                        # 计算新的库存和销量
                        new_stock = origin_stock - sku_count
                        new_sales = origin_sales + sku_count

                        # 减少商品库存，增加商品销量 乐观锁
                        result = SKU.objects.filter(id=sku_id, stock=origin_stock).update(stock=new_stock, sales=new_sales)
                        if result == 0:
                            continue  # 打断循环
                        # sku.stock -= sku_count
                        # sku.sales += sku_count
                        # sku.save()
                        spu = sku.goods
                        spu.sales += sku_count
                        spu.save()
                        # 保存订单商品数据
                        OrderGoods.objects.create(
                            order=order,
                            sku=sku,
                            count=sku_count,
                            price=sku.price
                        )
                        # 累加总数量和总价
                        order.total_count += sku_count
                        order.total_amount += sku.price * sku_count

                        break  # 跳出循环
                # 最后 加入邮费
                order.total_amount += order.freight
                order.save()
            except Exception:
                # 无论出现什么问题,全部回滚
                transaction.savepoint_rollback(save_point)
                raise
            else:
                transaction.savepoint_commit(save_point)
        # 清除购物车中已购买的商品
        pl = redis_coun.pipeline()
        pl.hdel('cart_%d', user.id, *cart_selected_ids)
        pl.srem('selected_%d' % user.id, *cart_selected_dict)
        pl.execute()

        return order


class CartSKUSerializer(serializers.ModelSerializer):
    """
    购物车商品数据序列化器
    """
    count = serializers.IntegerField(label='数量')

    class Meta:
        model = SKU
        fields = ('id', 'name', 'default_image_url', 'price', 'count')


class OrderSettlementSerializer(serializers.Serializer):
    """
    订单结算数据序列化器
    """
    freight = serializers.DecimalField(label='运费', max_digits=10, decimal_places=2)
    skus = CartSKUSerializer(many=True)