"""Historical approval records; direct Google registration supersedes invitations."""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from .models import EXTERNAL_ACCESS




@api_view(['GET', 'POST', 'PATCH'])
@permission_classes([IsAuthenticated])
def invitations(request):
    # Administrator/OSA flags deliberately do not confer invitation authority.
    if not request.user.is_superuser:
        raise PermissionDenied('Only the Super Admin can approve external accounts.')
    from .views import Response, page_response
    if request.method != 'GET':
        return Response({'message': 'External invitations are no longer required. Users can sign in directly with Google; manage account activation in Accounts & permissions.'}, status=410)
    def serialize(rows):
        return [{'id': r.pk, 'email': r.email, 'isActive': r.is_active,
                 'expiresAt': r.expires_at, 'accepted': r.accepted_user_id is not None,
                 'canSignIn': None} for r in rows]
    return page_response(EXTERNAL_ACCESS.objects.all(), request, serialize)
