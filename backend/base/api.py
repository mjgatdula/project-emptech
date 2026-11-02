"""JSON API using Django passwords, JWT authentication, and CSRF protection."""
import json
import hashlib
from functools import wraps

from django.conf import settings
from django.contrib.auth import authenticate, get_user_model, logout as django_logout
from django.contrib.auth.models import AnonymousUser
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError, RequestDataTooBig
from django.core.validators import validate_email
from django.db import DatabaseError, IntegrityError, InterfaceError, transaction, connection
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.views.decorators.cache import never_cache
from django.views.decorators.debug import sensitive_post_parameters, sensitive_variables
from django.views.decorators.http import require_GET, require_POST

from rest_framework.exceptions import AuthenticationFailed, ValidationError as APIValidationError
from rest_framework.throttling import SimpleRateThrottle
from .authentication import SchoolJWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.settings import api_settings as jwt_settings
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken
from rest_framework_simplejwt.tokens import RefreshToken

from .models import STUDENT_PROFILE, GOOGLE_IDENTITY
from .deployment_policy import RESERVED_EMAILS
from .permissions import is_administrator, is_osa, account_roles


class AccountThrottle(SimpleRateThrottle):
    scope = 'account_submit'
    rate = '20/min'

    def get_cache_key(self, request, view):
        return self.cache_format % {'scope': self.scope, 'ident': request.META.get('REMOTE_ADDR', '')}


def api_errors(view):
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        try:
            if request.method == 'POST':
                throttle = AccountThrottle()
                if not throttle.allow_request(request, None):
                    response = JsonResponse({'message': 'Too many account requests. Wait a minute and try again.'}, status=429)
                    response['Retry-After'] = str(max(1, int(throttle.wait() or 60)))
                    return response
            # API identity comes only from a verified Bearer token, never an admin cookie.
            authentication = SchoolJWTAuthentication().authenticate(request)
            request.user = authentication[0] if authentication else AnonymousUser()
            return view(request, *args, **kwargs)
        except (AuthenticationFailed, InvalidToken, TokenError):
            response = JsonResponse({'message': 'Your sign-in has expired or the token is invalid. Please sign in again.'}, status=401)
            response['WWW-Authenticate'] = 'Bearer'
            return response
        except APIValidationError:
            return JsonResponse({'message': 'A valid refresh token is required.'}, status=400)
        except RequestDataTooBig:
            return JsonResponse({'message': 'The request is too large.'}, status=413)
        except (json.JSONDecodeError, UnicodeDecodeError, TypeError):
            return JsonResponse({'message': 'Send a valid JSON object.'}, status=400)
        except (DatabaseError, InterfaceError):
            return JsonResponse({'message': 'The server could not access its database. Please try again later.'}, status=503)
    return wrapped


def body(request):
    if request.content_type != 'application/json':
        raise TypeError('Expected JSON')
    value = json.loads(request.body)
    if not isinstance(value, dict):
        raise TypeError('Expected an object')
    return value


def user_data(user):
    if not user.is_authenticated:
        return None
    return {
        'id': user.pk, 'username': user.username, 'email': user.email,
        'fullName': user.get_full_name() or user.username,
        'isStaff': user.is_staff, 'isSuperuser': user.is_superuser,
        'isAdmin': is_administrator(user), 'isOsa': is_osa(user),
        'roles': account_roles(user), 'role': account_roles(user)[0],
        'studentProfile': student_data(user),
        'googleLinked': GOOGLE_IDENTITY.objects.filter(user=user).exists(),
    }


def student_data(user):
    if 'student_profile' in user._state.fields_cache:
        profile = user._state.fields_cache['student_profile']
    else:
        profile = STUDENT_PROFILE.objects.select_related('site', 'program').filter(user=user).first()
    if profile is None:
        return None
    return {'studentNumber': profile.student_number, 'site': profile.site_id, 'siteName': profile.site.name,
        'program': profile.program_id, 'programName': profile.program.name, 'approvalStatus': profile.approval_status}


def session_data(request):
    user = user_data(request.user)
    return {'user': user, 'isAuthenticated': user is not None, 'csrfToken': get_token(request)}


@sensitive_variables('refresh')
def token_data(request, user):
    refresh = RefreshToken.for_user(user)
    return {
        'user': user_data(user), 'isAuthenticated': True,
        'csrfToken': get_token(request),
        'access': str(refresh.access_token), 'refresh': str(refresh),
    }


@never_cache
@require_GET
@api_errors
def session(request):
    return JsonResponse(session_data(request))


@never_cache
@require_POST
@sensitive_post_parameters('password')
@sensitive_variables('data', 'password')
@api_errors
def sign_in(request):
    if not getattr(settings, 'ALLOW_PASSWORD_AUTH', True):
        return JsonResponse({'message': 'Use your verified T.I.P. Google account. Password recovery is managed by Google.'}, status=403)
    data = body(request)
    identity = data.get('identity', '')
    password = data.get('password', '')
    if not isinstance(identity, str) or not isinstance(password, str) or not identity.strip() or not password:
        return JsonResponse({'message': 'Enter your email or username and password.'}, status=400)
    identity = identity.strip()
    User = get_user_model()
    # Prefer an exact username. Only resolve email when it identifies one user;
    # Django's default User.email has no database uniqueness constraint.
    username = identity
    if not User.objects.filter(username=identity).exists():
        candidates = list(User.objects.filter(email__iexact=identity).values_list('username', flat=True)[:2])
        if len(candidates) == 1:
            username = candidates[0]
    user = authenticate(request, username=username, password=password)
    if user is None:
        return JsonResponse({'message': 'Invalid email/username or password.'}, status=401)
    return JsonResponse(token_data(request, user))


@never_cache
@require_POST
@sensitive_post_parameters('password')
@sensitive_variables('data', 'password')
@api_errors
def register(request):
    if not getattr(settings, 'ALLOW_PASSWORD_AUTH', True):
        return JsonResponse({'message': 'Use your verified T.I.P. Google account. Password recovery is managed by Google.'}, status=403)
    if request.user.is_authenticated:
        return JsonResponse({'message': 'Sign out before creating another account.'}, status=409)
    data = body(request)
    fields = ['username', 'email', 'fullName', 'password']
    if any(not isinstance(data.get(field), str) or not data[field].strip() for field in fields):
        return JsonResponse({'message': 'Full name, username, email, and password are required.'}, status=400)
    username, email, full_name = (data[field].strip() for field in fields[:3])
    password = data['password']
    if email.casefold() in RESERVED_EMAILS:
        return JsonResponse({'message': 'This administrator email must sign in through verified Google identity.'}, status=403)
    User = get_user_model()
    if len(username) > 150 or len(email) > 254 or len(full_name) > 150:
        return JsonResponse({'message': 'One or more account fields exceed the maximum length.'}, status=400)
    try:
        User._meta.get_field('username').run_validators(username)
        validate_email(email)
        first, _, last = full_name.partition(' ')
        user = User(username=username, email=User.objects.normalize_email(email), first_name=first, last_name=last)
        validate_password(password, user=user)
    except ValidationError as error:
        return JsonResponse({'message': ' '.join(error.messages)}, status=400)
    try:
        with transaction.atomic():
            # Serialize matching registrations without replacing Django's User schema.
            # PostgreSQL releases these transaction-scoped locks on commit/rollback.
            identities = ['username:' + username.casefold(), 'email:' + email.casefold()]
            lock_ids = sorted({int.from_bytes(hashlib.sha256(value.encode()).digest()[:8], signed=True) for value in identities})
            with connection.cursor() as cursor:
                for lock_id in lock_ids:
                    cursor.execute('SELECT pg_advisory_xact_lock(%s)', [lock_id])
            if User.objects.filter(username__iexact=username).exists():
                return JsonResponse({'message': 'That username is already in use.'}, status=409)
            if User.objects.filter(email__iexact=email).exists():
                return JsonResponse({'message': 'That email is already registered.'}, status=409)
            # Privilege flags never come from request data.
            user.set_password(password)
            user.is_staff = False
            user.is_superuser = False
            user.save()
            result = token_data(request, user)
    except IntegrityError:
        return JsonResponse({'message': 'That account could not be created. Try a different username.'}, status=409)
    return JsonResponse(result, status=201)


@never_cache
@require_POST
@sensitive_variables('data', 'raw', 'token', 'serializer')
@api_errors
def refresh_token(request):
    data = body(request)
    raw = data.get('refresh')
    if not isinstance(raw, str) or not raw:
        return JsonResponse({'message': 'A refresh token is required.'}, status=400)
    token = RefreshToken(raw)
    SchoolJWTAuthentication().get_user(token)
    # Serialize rotation of the same refresh token across tabs/processes.
    with transaction.atomic():
        OutstandingToken.objects.select_for_update().filter(jti=token[jwt_settings.JTI_CLAIM]).first()
        serializer = TokenRefreshSerializer(data={'refresh': raw})
        serializer.is_valid(raise_exception=True)
        result = dict(serializer.validated_data)
    return JsonResponse(result)


@never_cache
@require_POST
@sensitive_variables('data', 'raw', 'token')
@api_errors
def sign_out(request):
    data = body(request)
    raw = data.get('refresh')
    if not isinstance(raw, str) or not raw:
        return JsonResponse({'message': 'A refresh token is required.'}, status=400)
    try:
        token = RefreshToken(raw)
        with transaction.atomic():
            OutstandingToken.objects.select_for_update().filter(jti=token[jwt_settings.JTI_CLAIM]).first()
            token.blacklist()
    except TokenError:
        # An expired/already-revoked refresh token cannot renew a login.
        pass
    django_logout(request)
    return JsonResponse({'user': None, 'isAuthenticated': False, 'csrfToken': get_token(request)})


@never_cache
@require_GET
@api_errors
def profile(request):
    if not request.user.is_authenticated:
        return JsonResponse({'message': 'Sign in to view your profile.'}, status=401)
    return JsonResponse({'user': user_data(request.user)})



def csrf_failure(request, reason=''):
    return JsonResponse({'message': 'Your security token is missing or expired. Refresh the page and try again.', 'code': 'csrf_failed'}, status=403)


@never_cache
@require_POST
@sensitive_post_parameters('current_password', 'new_password')
@sensitive_variables('data', 'current', 'new')
@api_errors
def change_password(request):
    if not getattr(settings, 'ALLOW_PASSWORD_AUTH', True):
        return JsonResponse({'message': 'Use your verified T.I.P. Google account. Password recovery is managed by Google.'}, status=403)
    if not request.user.is_authenticated:
        return JsonResponse({'message': 'Sign in first.'}, status=401)
    data = body(request)
    current, new = data.get('current_password'), data.get('new_password')
    if not isinstance(current, str) or not isinstance(new, str) or not request.user.check_password(current):
        return JsonResponse({'message': 'The current password is incorrect.'}, status=400)
    try:
        validate_password(new, user=request.user)
    except ValidationError as error:
        return JsonResponse({'message': ' '.join(error.messages)}, status=400)
    with transaction.atomic():
        request.user.set_password(new)
        request.user.save(update_fields=['password'])
        result = token_data(request, request.user)
    return JsonResponse(result)
