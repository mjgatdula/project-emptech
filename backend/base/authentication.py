"""A production JWT must still belong to an active verified school Google account."""
from django.conf import settings
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.authentication import JWTAuthentication
from .models import GOOGLE_IDENTITY
from .access_policy import is_school_email, external_access_allowed


class SchoolJWTAuthentication(JWTAuthentication):
    def get_user(self, validated_token):
        user = super().get_user(validated_token)
        if not getattr(settings, 'ALLOW_PASSWORD_AUTH', True):
            email = user.email.casefold()
            if (not GOOGLE_IDENTITY.objects.filter(user=user, verified_email=email).exists()
                or (not is_school_email(email) and not external_access_allowed(user))):
                raise AuthenticationFailed('Sign in with a verified Google account. External accounts must remain ordinary users.', code='google_required')
        return user
