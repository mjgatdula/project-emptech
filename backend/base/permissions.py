"""Explicit application roles, separate from Django admin-site eligibility."""
from rest_framework.permissions import BasePermission
from rest_framework.exceptions import PermissionDenied
from .models import STAFF_SITE_ASSIGNMENT

ADMIN_GROUP = 'TIPPED Administrators'
OSA_GROUP = 'TIPPED OSA'


def role_groups(user):
    if not user.is_authenticated:
        return set()
    if not hasattr(user, '_tipped_role_groups'):
        user._tipped_role_groups = {group.name for group in user.groups.all()}
    return user._tipped_role_groups


def is_administrator(user):
    return bool(user.is_authenticated and user.is_active and (user.is_superuser or ADMIN_GROUP in role_groups(user)))


def is_osa(user):
    return bool(user.is_authenticated and user.is_active and (user.is_superuser or OSA_GROUP in role_groups(user)))


def account_roles(user):
    if user.is_superuser:
        return ['superadmin']
    roles = []
    if ADMIN_GROUP in role_groups(user):
        roles.append('admin')
    if OSA_GROUP in role_groups(user):
        roles.append('osa')
    if roles:
        return roles
    from .deployment_policy import SCHOOL_DOMAIN
    return ['student'] if user.email.casefold().split('@')[-1] == SCHOOL_DOMAIN else ['guest']


def is_privileged_account(user):
    # Conservatively protect all existing Django privileges, not only our two groups.
    return bool(user.is_superuser or user.is_staff or user.groups.exists() or
                user.user_permissions.exists() or any(row.is_active for row in user.staff_site_assignments.all()))


def ordinary_accounts(records):
    return records.filter(is_superuser=False, is_staff=False, groups__isnull=True,
                          user_permissions__isnull=True).exclude(
        staff_site_assignments__is_active=True).distinct()


def staff_sites(user):
    if not is_osa(user):
        return []
    if not hasattr(user, '_campus_site_ids'):
        user._campus_site_ids = list(STAFF_SITE_ASSIGNMENT.objects.filter(
            user=user, is_active=True, site__is_active=True).values_list('site_id', flat=True))
    return user._campus_site_ids


def can_manage(user, report):
    return bool(is_osa(user) and (user.is_superuser or report.site_id in staff_sites(user)))


def require_manager(user, report):
    if not can_manage(user, report):
        raise PermissionDenied('This report is outside your OSA campus permissions.')


class IsCampusStaff(BasePermission):
    def has_permission(self, request, view):
        return is_osa(request.user)


class IsAccountAdministrator(BasePermission):
    def has_permission(self, request, view):
        return is_administrator(request.user)
