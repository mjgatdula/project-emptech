"""Verified Google registration policy; external identities stay ordinary users."""
from django.contrib.auth import get_user_model
from .deployment_policy import SCHOOL_DOMAIN


def is_school_email(email):
    return email.casefold().split('@')[-1] == SCHOOL_DOMAIN


def external_access_allowed(user):
    return get_user_model().objects.filter(
        pk=user.pk, email=user.email, is_active=True, is_staff=False,
        is_superuser=False, groups__isnull=True, user_permissions__isnull=True,
    ).exclude(staff_site_assignments__is_active=True).exists()
