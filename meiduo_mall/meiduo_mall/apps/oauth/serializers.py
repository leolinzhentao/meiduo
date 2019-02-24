from rest_framework import serializers
from django_redis import get_redis_connection

from users.models import User
from .utils import check_save_user_token
from .models import OAuthQQUser


class QQAuthUserSerializer(serializers.Serializer):
    """绑定用户的序列化器"""

    access_token = serializers.CharField(label='操作凭证')
    mobile = serializers.RegexField(label='手机号', regex=r'^1[3-9]\d{9}$')
    password = serializers.CharField(label='密码', max_length=20, min_length=8)
    sms_code = serializers.CharField(label='短信验证码')

    def validate(self, attrs):
        access_token = attrs.get('access_token')  # 获取出加密的openid
        openid = check_save_user_token(access_token)
        if not openid:
            raise serializers.ValidationError('openid无效')
        attrs['access_token'] = openid   # 把解密后的openid保存到反序列化器中

        # 验证短信验证码是否正确
        redis_conn = get_redis_connection('verify_codes')
        # 获取当前用户的手机号
        mobile = attrs.get('mobile')
        real_sms_code = redis_conn.get('sms_%s' % mobile)
        # 获取前端传过来的验证码
        sms_code = attrs.get('sms_code')
        if real_sms_code.decode() != sms_code:   # 从redis中取出来的数据都是bytes类型，需decode后才可以使用
            raise serializers.ValidationError('验证码错误')

        try:
            # 判断手机号是否已注册
            user = User.objects.get(mobile=mobile)
        except User.DoesNotExist:
            # 如果查询不到，说明手机未注册
            pass

        else:
            # 查询到用户则证明，手机号已注册过，校验密码是否正确
            if not user.check_password(attrs.get('password')):
                raise serializers.ValidationError('手机号已注册，但密码错误！')
            else:
                attrs['user'] = user

        return attrs

    def create(self, validated_data):
        """把openid和user进行绑定"""
        user = validated_data.get('user')
        if not user:   # 如果用户是不存在的， 那就新增一个用户
            user = User(
                username=validated_data.get('mobile'),
                password=validated_data.get('password'),
                mobile=validated_data.get('mobile')
            )
            user.set_password(validated_data.get('password'))
            user.save()

        # 让user和openid绑定
        OAuthQQUser.objects.create(
            user=user,
            openid=validated_data.get('access_token')
        )
        return user
