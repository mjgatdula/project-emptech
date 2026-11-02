import time
from django.conf import settings
from django.shortcuts import redirect
from django import forms
from django.contrib import admin
from django.contrib.admin.forms import AdminAuthenticationForm
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin, GroupAdmin
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.db import models
from .models import (PROGRAM, SITE, CATEGORY, OFFICE, STUDENT_PROFILE, STAFF_SITE_ASSIGNMENT,
    ITEM_REPORT, MODERATION_DECISION, CUSTODY_RECEIPT, OWNERSHIP_CLAIM, CLAIM_EVIDENCE,
    RELEASE_RECORD, REPORT_CLOSURE, NOTIFICATION, AUDIT_EVENT, GOOGLE_IDENTITY)


class SuperuserLoginForm(AdminAuthenticationForm):
    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)
        if not user.is_superuser:
            raise ValidationError('Django administration is restricted to Super Admin accounts.', code='invalid_login')


class SuperuserAdminSite(admin.AdminSite):
    login_form = SuperuserLoginForm

    def has_permission(self, request):
        allowed = bool(request.user.is_active and request.user.is_staff and request.user.is_superuser)
        if not allowed or getattr(settings, 'ALLOW_PASSWORD_AUTH', True):
            return allowed
        identity = getattr(request.user, 'google_identity', None)
        verified = request.session.get('google_verified_at', 0)
        return bool(identity and isinstance(verified, (int, float)) and 0 <= time.time()-verified < 900
            and request.session.get('google_verified_subject') == identity.subject)

    def login(self, request, extra_context=None):
        if not getattr(settings, 'ALLOW_PASSWORD_AUTH', True):
            return redirect(getattr(settings, 'FRONTEND_LOGIN_URL', '/login'))
        return super().login(request, extra_context)



site = SuperuserAdminSite(name='admin')
site.register(get_user_model(), UserAdmin)
site.register(Group, GroupAdmin)


class PrivateUploadWidget(forms.ClearableFileInput):
    def is_initial(self, value):
        # Private storage deliberately has no public .url property.
        return False


class ConfigurationAdmin(admin.ModelAdmin):
    def has_module_permission(self, request):
        return request.user.is_superuser

    def has_view_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


@admin.register(ITEM_REPORT, site=site)
class ReportAdmin(ConfigurationAdmin):
    list_display = ['reference_number', 'title', 'report_type', 'site', 'reporter', 'created_at']
    list_filter = ['report_type', 'site', 'category']
    search_fields = ['reference_number', 'title', 'location']
    readonly_fields = ['id', 'created_at', 'updated_at']
    formfield_overrides = {models.ImageField: {'widget': PrivateUploadWidget}}


class HistoryAdmin(ConfigurationAdmin):
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


for model in [PROGRAM, SITE, CATEGORY, OFFICE, STUDENT_PROFILE, STAFF_SITE_ASSIGNMENT]:
    site.register(model, ConfigurationAdmin)
for model in [MODERATION_DECISION, CUSTODY_RECEIPT, OWNERSHIP_CLAIM, CLAIM_EVIDENCE, RELEASE_RECORD, REPORT_CLOSURE, NOTIFICATION, AUDIT_EVENT, GOOGLE_IDENTITY]:
    site.register(model, HistoryAdmin)
site.site_header = 'TIPPED Administration'
site.site_title = 'TIPPED Admin'
site.index_title = 'Campus configuration and records'
