from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend

User = get_user_model()


class PhoneBackend(ModelBackend):
    """Authenticate using the phone number as the username field."""

    def authenticate(self, request, phone=None, username=None, password=None, **kwargs):
        phone = phone or username
        if phone is None or password is None:
            return None
        try:
            user = User.objects.get(phone=phone)
        except User.DoesNotExist:
            return None
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
