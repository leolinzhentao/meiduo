from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from django_redis import get_redis_connection
from random import randint
import logging
from . import constants
from celery_tasks.sms.tasks import send_sms_code

logger = logging.getLogger('django')  # 创建日志输出器


class SMSCodeView(APIView):
    """
    发送短信验证码
    """

    def get(self, request, mobile):

        # 创建redis对象
        redis_conn = get_redis_connection('verify_codes')

        # 60秒内不允许重复发送短信
        send_flag = redis_conn.get('send_flag_%s' % mobile)
        if send_flag:
            return Response({'message': '频繁发送短信'}, status=status.HTTP_400_BAD_REQUEST)

        # 生成发送短信验证码
        sms_code = '%06d' % randint(0, 999999)
        print(sms_code)
        logger.debug(sms_code)

        # 发送短信验证码
        send_sms_code.delay(mobile, sms_code)

        # CCP().send_template_sms(mobile, [sms_code, constants.SMS_CODE_REDIS_EXPIRES//60], constants.SEND_SMS_TEMPLATE_ID)

        # 使用redis管道pipeline对象存储短信验证码和标记
        pl = redis_conn.pipeline()
        pl.setex("sms_%s" % mobile, constants.SMS_CODE_REDIS_EXPIRES, sms_code)
        pl.setex("send_flag_%s" % mobile, constants.SEND_SNS_CODE_INTERVAL, 1)

        # 执行管道
        pl.execute()

        # 响应
        return Response({"message": "OK"})



