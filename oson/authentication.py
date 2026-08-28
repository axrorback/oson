import secrets
from django.conf import settings
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed


class OsonAuthentication(BaseAuthentication):

    def authenticate(self, request):
        token = request.headers.get("token")

        if not token:
            raise AuthenticationFailed("Token is required.",)

        if not secrets.compare_digest(
            token,
            settings.OSON_SECRET_TOKEN,
        ):
            raise AuthenticationFailed("Invalid token.",)

        return OsonMerchantUser(),None,


class OsonMerchantUser:
    is_authenticated = True