"""Shared Google account eligibility; no view or HTTP imports."""
from django.utils import timezone
from .models import EXTERNAL_ACCESS
from .deployment_policy import SCHOOL_DOMAIN


def is_school_email(email):
    return email.casefold().split('@')[-1] == SCHOOL_DOMAIN


def external_access_allowed(user):
    return EXTERNAL_ACCESS.objects.filter(
        email=user.email.casefold(), accepted_user=user, is_active=True,
        expires_at__gt=timezone.now(), accepted_user__is_staff=False,
        accepted_user__is_superuser=False, accepted_user__groups__isnull=True,
        accepted_user__user_permissions__isnull=True,
    ).exclude(accepted_user__staff_site_assignments__is_active=True).exists()


