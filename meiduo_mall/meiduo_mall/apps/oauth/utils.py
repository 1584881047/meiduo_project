from itsdangerous import TimedJSONWebSignatureSerializer
from django.conf import settings


class MD5(object):
    def __init__(self, value):
        self.serializer = TimedJSONWebSignatureSerializer(secret_key=settings.SECRET_KEY, expires_in=300)
        self.value = value

    def generate_access_token(self):
        new_value = self.serializer.dumps(self.value)
        return new_value.decode()

    def check_access_token(self):
        try:
            new_value = self.serializer.loads(self.value)
        except:
            return None

        return new_value
