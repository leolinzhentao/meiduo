import logging

from celery_tasks.main import celery_app
from .yuntongxun.sms import CCP
from . import constants

logger = logging.getLogger('django')

@celery_app.task(name="send_sms_code")
def send_sms_code(mobile, code):
    """
    发送短信验证码
    :param mobile:手机号
    :param code: 验证码
    :return: 响应
    """
    try:
        ccp = CCP()
        result = ccp.send_template_sms(mobile, [code, constants.SMS_CODE_REDIS_EXPIRES // 60], constants.SEND_SMS_TEMPLATE_ID)
    except Exception as e:
        logger.error("发送验证码短信[异常][ mobile: %s, message: %s ]" % (mobile, e))
    else:
        if result == 0:
            logger.info("发送验证码短信[正常][ mobile: %s ]" % mobile)
        else:
            logger.warning("发送验证码短信[失败][ mobile: %s ]" % mobile)
