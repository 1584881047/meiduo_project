from django.contrib.auth.models import AbstractUser
from django.db import models
from itsdangerous import TimedJSONWebSignatureSerializer
from django.conf import settings


# Create your models here.
class User(AbstractUser):
    mobile = models.CharField(max_length=11, unique=True, verbose_name='手机号')
    email_active = models.BooleanField(default=False, verbose_name='邮箱验证状态')

    class Mate:
        db_table = 'tb_users'
        verbose_name = '用户'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.username

    def generate_verify_email_url(self):
        """
        生成邮箱验证码
        :return:
        """
        dict = {
            'user_id': self.id,
            'email': self.email
        }
        serializer = TimedJSONWebSignatureSerializer(secret_key=settings.SECRET_KEY,
                                                     expires_in=600
                                                     )
        token = serializer.dumps(dict).decode()

        verify_url = settings.EMAIL_VERIFY_URL + '?token=' + token

        return verify_url

    @staticmethod
    def check_verify_email_token(token):
        serializer = TimedJSONWebSignatureSerializer(secret_key=settings.SECRET_KEY,
                                                     expires_in=600
                                                     )

        try:
            data = serializer.loads(token)
        except BaseException as e:
            return None

        user_id = data.get('user_id')
        email = data.get('email')
        try:
            user = User.objects.get(id=user_id, email=email)
        except BaseException as e:
            print(e)
            return  None
        return user
