from celery_tasks.main import celery_app
from celery_tasks.yuntongxun.ccp_sms import CCP


# 创建人物并且用celery实列的task方法装饰
@celery_app.task(bind=True,name = 'send_code',retry_backoff=3)
def send_code(self,mobile,sms_code):
    """
     发送短信异步任务
     :param mobile: 手机号
     :param sms_code: 短信验证码
     :return: 成功0 或 失败-1
     """

    # try:
        # 调用 CCP() 发送短信, 并传递相关参数:
    result = CCP().send_template_sms(mobile,
                                         [sms_code, 5],
                                         1)

    print(result)
    # except Exception as e:
    #     # 如果发送过程出错, 打印错误日志
    #     print(e)
    #
    #     # 有异常自动重试三次
    #     raise self.retry(exc=e, max_retries=3)

    # 如果发送成功, rend_ret 为 0:
    # if result != 0:
        # 有异常自动重试三次
        # raise self.retry(exc=Exception('发送短信失败'), max_retries=3)

    return result