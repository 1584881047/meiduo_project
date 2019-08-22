import os
# 配置django环境
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "meiduo_mall.settings.dev")
# 导入Celery
from celery import Celery


celery_app = Celery('app')

# 配置broker_url
celery_app.config_from_object('celery_tasks.config')

# 让 celery_app 自动捕获目标地址下的任务
celery_app.autodiscover_tasks(['celery_tasks.sms'])
