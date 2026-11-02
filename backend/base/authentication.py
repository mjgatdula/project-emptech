"""A production JWT must still belong to an active verified school Google account."""
from django.conf import settings
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.authentication import JWTAuthentication
from .models import GOOGLE_IDENTITY
from .deployment_policy import SCHOOL_DOMAIN


class SchoolJWTAuthentication(JWTAuthentication):
    def get_user(self, validated_token):
        user = super().get_user(validated_token)
        if not getattr(settings, 'ALLOW_PASSWORD_AUTH', True):
            email = user.email.casefold()
            if not email.endswith('@'+SCHOOL_DOMAIN) or not GOOGLE_IDENTITY.objects.filter(user=user, verified_email=email).exists():
                raise AuthenticationFailed('Sign in with your verified school Google account.', code='google_required')
        return user
