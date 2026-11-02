"""Google Identity Services: verified Workspace identity, one-time session nonce."""
import hashlib
import secrets
import time
import jwt
from django.conf import settings
from django.contrib.auth import get_user_model, login as django_login
from django.contrib.auth.models import Group
from django.contrib.sessions.models import Session
from django.db import connection, transaction
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.debug import sensitive_post_parameters, sensitive_variables
from django.views.decorators.http import require_GET, require_POST
from jwt.exceptions import PyJWKClientConnectionError, PyJWKClientError, PyJWTError
from .api import api_errors, body, token_data, AccountThrottle
from .deployment_policy import SCHOOL_DOMAIN, INITIAL_SUPERADMIN, INITIAL_ADMINS
from .models import GOOGLE_IDENTITY, AUDIT_EVENT
from .permissions import ADMIN_GROUP

class ChallengeThrottle(AccountThrottle):
    scope = 'google_challenge'
    rate = '30/min'


keys = jwt.PyJWKClient('https://www.googleapis.com/oauth2/v3/certs', timeout=5, lifespan=300)


@never_cache
@require_GET
def configuration(request):
    return JsonResponse({'googleClientId': getattr(settings, 'GOOGLE_CLIENT_ID', ''),
        'schoolDomain': SCHOOL_DOMAIN, 'passwordAuthEnabled': getattr(settings, 'ALLOW_PASSWORD_AUTH', True)})


@never_cache
@require_GET
@api_errors
def challenge(request):
    if not getattr(settings, 'GOOGLE_CLIENT_ID', ''):
        return JsonResponse({'message': 'Google sign-in is unavailable. Contact the site administrator.'}, status=503)
    throttle = ChallengeThrottle()
    if not throttle.allow_request(request, None):
        return JsonResponse({'message': 'Too many sign-in requests. Wait a minute and retry.'}, status=429)
    now = time.time()
    nonces = {k:v for k,v in request.session.get('google_nonces', {}).items() if isinstance(v, (int, float)) and now-v < 600}
    nonce = secrets.token_urlsafe(32)
    # Bound per-session storage; keep recent tabs valid independently.
    nonces = dict(sorted(nonces.items(), key=lambda row: row[1])[-4:])
    nonces[nonce] = now
    request.session['google_nonces'] = nonces
    request.session.save()
    return JsonResponse({'nonce': nonce})


def verify_credential(raw):
    signing_key = keys.get_signing_key_from_jwt(raw)
    client = settings.GOOGLE_CLIENT_ID
    claims = jwt.decode(raw, signing_key.key, algorithms=['RS256'], audience=client,
        issuer=['accounts.google.com', 'https://accounts.google.com'], leeway=30,
        options={'require': ['iss','aud','sub','iat','exp','nonce','email','email_verified','hd'], 'strict_aud': True})
    if claims.get('azp', client) != client:
        raise ValueError('Invalid authorized party')
    email, subject = claims.get('email'), claims.get('sub')
    if (not isinstance(email, str) or len(email)>254 or email.casefold().split('@')[-1] != SCHOOL_DOMAIN
        or email.count('@') != 1 or claims.get('email_verified') is not True or claims.get('hd') != SCHOOL_DOMAIN
        or not isinstance(subject, str) or not subject or len(subject)>255
        or not isinstance(claims.get('nonce'), str)):
        raise ValueError('A verified school Workspace account is required')
    return claims


class IdentityConflict(Exception):
    pass


@never_cache
@require_POST
@sensitive_post_parameters('credential')
@sensitive_variables('raw', 'claims', 'result')
@api_errors
def sign_in(request):
    if not getattr(settings, 'GOOGLE_CLIENT_ID', ''):
        return JsonResponse({'message': 'Google sign-in is unavailable. Contact the site administrator.'}, status=503)
    data = body(request)
    raw = data.get('credential')
    if not isinstance(raw, str) or not raw or len(raw)>16384:
        return JsonResponse({'message': 'A Google sign-in credential is required.'}, status=400)
    try:
        claims = verify_credential(raw)
    except PyJWKClientConnectionError:
        return JsonResponse({'message': 'Google verification is temporarily unavailable. Try again later.'}, status=503)
    except (PyJWTError, PyJWKClientError, ValueError, TypeError):
        return JsonResponse({'message': 'Use a valid, verified @tip.edu.ph Google account. Please try signing in again.'}, status=401)
    try:
        with transaction.atomic():
            # Verify and consume against the locked database session, not a stale tab copy.
            session = Session.objects.select_for_update().filter(session_key=request.session.session_key, expire_date__gt=timezone.now()).first()
            if not session:
                raise IdentityConflict('The sign-in request expired. Retry Google sign-in.')
            state = session.get_decoded()
            nonces = state.get('google_nonces', {})
            issued = nonces.pop(claims['nonce'], None)
            if not isinstance(issued, (int, float)) or not 0 <= time.time()-issued < 600:
                raise IdentityConflict('The sign-in request expired or was already used. Retry Google sign-in.')
            state['google_nonces'] = nonces
            session.session_data = request.session.encode(state)
            session.save(update_fields=['session_data'])
            email = claims['email'].casefold()
            username = 'google_' + hashlib.sha256(claims['sub'].encode()).hexdigest()[:40]
            lock_ids = sorted({int.from_bytes(hashlib.sha256(v.encode()).digest()[:8], signed=True)
                for v in ['email:'+email, 'username:'+username]})
            with connection.cursor() as cursor:
                for lock_id in lock_ids:
                    cursor.execute('SELECT pg_advisory_xact_lock(%s)', [lock_id])
            User = get_user_model()
            identity = GOOGLE_IDENTITY.objects.select_related('user').filter(subject=claims['sub']).first()
            created = False
            if identity:
                user = User.objects.select_for_update().get(pk=identity.user_id)
                if user.email.casefold() != email or identity.verified_email != email:
                    raise IdentityConflict('This Google identity needs administrator review because its email changed.')
                if data.get('link') is True and (not request.user.is_authenticated or request.user.pk != user.pk):
                    raise IdentityConflict('Sign in to the matching existing account before linking Google.')
            else:
                matches = list(User.objects.select_for_update().filter(email__iexact=email)[:2])
                if matches:
                    # Never trust an email-only legacy registration as ownership proof.
                    if len(matches)!=1 or not request.user.is_authenticated or request.user.pk != matches[0].pk or data.get('link') is not True:
                        raise IdentityConflict('An account already uses this email. Sign in to that account and link Google from Profile, or contact the owner.')
                    user = matches[0]
                    if GOOGLE_IDENTITY.objects.filter(user=user).exists():
                        raise IdentityConflict('This account is already linked to a different Google identity.')
                else:
                    if data.get('link') is True:
                        raise IdentityConflict('Sign in to the matching existing account before linking Google.')
                    name = claims.get('name')
                    name = name[:150] if isinstance(name, str) else email.split('@')[0]
                    first, _, last = name.partition(' ')
                    user = User(username=username, email=email, first_name=first, last_name=last)
                    user.set_unusable_password()
                    user.save()
                if not user.is_active:
                    raise IdentityConflict('This account is inactive. Contact the administrator.')
                GOOGLE_IDENTITY.objects.create(user=user, subject=claims['sub'], verified_email=email)
                created = True
            if not user.is_active:
                raise IdentityConflict('This account is inactive. Contact the administrator.')
            if created:
                # Bootstrap only once, from server-verified identity. Later removals stay removed.
                if email == INITIAL_SUPERADMIN:
                    user.is_superuser = user.is_staff = True
                    user.save(update_fields=['is_superuser','is_staff'])
                elif email in INITIAL_ADMINS:
                    group, _ = Group.objects.get_or_create(name=ADMIN_GROUP)
                    user.groups.add(group)
                AUDIT_EVENT.objects.create(actor=user, action='google_identity_linked', detail='Verified school Google identity; initial role policy applied.')
            result = token_data(request, user)
            request.session['google_nonces'] = nonces
            if user.is_superuser:
                # A Google-verified Super Admin can also enter the protected Django admin.
                django_login(request, user, backend='django.contrib.auth.backends.ModelBackend')
                request.session['google_verified_subject'] = claims['sub']
                request.session['google_verified_at'] = time.time()
                from django.middleware.csrf import get_token
                result['csrfToken'] = get_token(request)
        return JsonResponse(result)
    except IdentityConflict as error:
        return JsonResponse({'message': str(error)}, status=409)
