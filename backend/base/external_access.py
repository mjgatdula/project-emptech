"""Super Admin approvals; external access is rechecked on every JWT use."""
import hashlib
from datetime import timedelta
from django.contrib.auth import get_user_model
from django.db import connection, transaction
from django.utils import timezone
from rest_framework import serializers
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from .models import EXTERNAL_ACCESS, AUDIT_EVENT
from .permissions import is_privileged_account


from .access_policy import is_school_email


@api_view(['GET', 'POST', 'PATCH'])
@permission_classes([IsAuthenticated])
def invitations(request):
    # Administrator/OSA flags deliberately do not confer invitation authority.
    if not request.user.is_superuser:
        raise PermissionDenied('Only the Super Admin can approve external accounts.')
    from .views import Response, page_response
    if request.method == 'POST':
        email = serializers.EmailField(max_length=254).run_validation(request.data.get('email')).casefold()
        days = serializers.IntegerField(min_value=1, max_value=365).run_validation(request.data.get('days', 30))
        if is_school_email(email):
            raise ValidationError('TIP school accounts do not need an external invitation.')
        with transaction.atomic():
            lock_id = int.from_bytes(hashlib.sha256(('email:' + email).encode()).digest()[:8], signed=True)
            with connection.cursor() as cursor:
                cursor.execute('SELECT pg_advisory_xact_lock(%s)', [lock_id])
            existing_users = list(get_user_model().objects.filter(email__iexact=email).prefetch_related('groups', 'user_permissions', 'staff_site_assignments')[:2])
            if len(existing_users) > 1 or any(is_privileged_account(u) for u in existing_users):
                raise ValidationError('This identity requires owner review; external access cannot grant privileged roles.')
            row = EXTERNAL_ACCESS.objects.select_for_update().filter(email=email).first()
            if row is None:
                row = EXTERNAL_ACCESS(email=email, invited_by=request.user)
            row.is_active = True
            row.expires_at = timezone.now() + timedelta(days=days)
            row.save()
            AUDIT_EVENT.objects.create(actor=request.user, action='external_access_approved', detail=f'External approval {row.pk}; expires {row.expires_at.isoformat()}')
        return Response({'message': 'External email approved. The person can now sign in with Google. No email was sent.'}, status=201)
    if request.method == 'PATCH':
        pk = serializers.UUIDField().run_validation(request.data.get('id'))
        with transaction.atomic():
            row = EXTERNAL_ACCESS.objects.select_for_update().filter(pk=pk).first()
            if row is None:
                raise ValidationError('External approval not found.')
            row.is_active = False
            row.save(update_fields=['is_active'])
            AUDIT_EVENT.objects.create(actor=request.user, action='external_access_revoked', detail=f'External approval {row.pk} revoked.')
        return Response({'message': 'External access revoked. Existing access and refresh tokens will no longer authorize requests.'})
    def serialize(rows):
        now = timezone.now()
        return [{'id': r.pk, 'email': r.email, 'isActive': r.is_active,
                 'expiresAt': r.expires_at, 'accepted': r.accepted_user_id is not None,
                 'canSignIn': r.is_active and r.expires_at > now} for r in rows]
    return page_response(EXTERNAL_ACCESS.objects.all(), request, serialize)
