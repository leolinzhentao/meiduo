from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from django.conf import settings
from itsdangerous import BadData


def generate_save_user_token(openid):
    """对openid进行加密"""
    # 1.创建序列化器对象
    serializer = Serializer(settings.SECRET_KEY, 600)
    data = {'openid': openid}
    # 2.调用序列化器的dumps
    access_token_bytes = serializer.dumps(data)

    # 3.把加密后的openid返回
    return access_token_bytes.decode()

def check_save_user_token(openid):
    """对加密的openid进行解密"""
    # 1.创建序列化器对象
    serializer = Serializer(settings.SECRET_KEY, 600)
    try:
        # 2.调用loads方法对数据进行解密
        data = serializer.loads(openid)
    except BadData:
        return None
    else:
        return data.get('openid')