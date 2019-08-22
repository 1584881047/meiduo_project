import re

from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.hashers import check_password

from users.models import User


class UsernameMobileAuthBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):

        user = self.get_user_by_account(username)
        if user and user.check_password(password):
            return user
        else:
            return None

    def get_user_by_account(self, account):
        try:
            if re.match(r'^1[3-9]\d{9}$', account):
                user = User.objects.get(mobile=account)
            else:
                user = User.objects.get(username=account)
        except BaseException as e:
            return None
        else:
            return user
