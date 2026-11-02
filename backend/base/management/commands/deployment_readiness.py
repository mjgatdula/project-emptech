"""Read-only release gates; successful code checks alone do not authorize publishing."""
import os
from pathlib import Path
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from base.models import GOOGLE_IDENTITY
from base.deployment_policy import INITIAL_SUPERADMIN


class Command(BaseCommand):
    help = 'Read-only production readiness checks. Prints checks only, never secret values.'

    def handle(self, *args, **options):
        checks = {
            'Production DEBUG disabled': not settings.DEBUG,
            'Google Web Client ID configured': bool(getattr(settings,'GOOGLE_CLIENT_ID','')) and 'replace-' not in settings.GOOGLE_CLIENT_ID,
            'Google-only website authentication': not getattr(settings,'ALLOW_PASSWORD_AUTH',True),
            'Explicit public hostnames': bool(settings.ALLOWED_HOSTS) and all(h not in {'*','localhost','127.0.0.1','[::1]'} for h in settings.ALLOWED_HOSTS),
            'HTTPS redirect and secure cookies': settings.SECURE_SSL_REDIRECT and settings.SESSION_COOKIE_SECURE and settings.CSRF_COOKIE_SECURE,
            'Separate strong Django/JWT secrets': len(settings.SECRET_KEY)>=50 and len(settings.SIMPLE_JWT['SIGNING_KEY'])>=50 and settings.SECRET_KEY!=settings.SIMPLE_JWT['SIGNING_KEY'],
            'Shared throttle cache': settings.CACHES['default']['BACKEND'].endswith('DatabaseCache'),
            'Frontend production bundle': (settings.FRONTEND_DIST/'index.html').is_file() if hasattr(settings,'FRONTEND_DIST') else False,
            'Private durable storage configured': (getattr(settings, 'PRIVATE_STORAGE_BACKEND', 'filesystem') == 's3' or (Path(settings.PRIVATE_MEDIA_ROOT).is_dir() and os.access(settings.PRIVATE_MEDIA_ROOT, os.W_OK))),
        }
        if getattr(settings, 'PRIVATE_STORAGE_BACKEND', 'filesystem') == 's3':
            try:
                from base.models import private_evidence_storage
                storage = private_evidence_storage()
                storage.connection.meta.client.head_bucket(Bucket=storage.bucket_name)
                checks['Private storage provider reachable'] = True
            except Exception:
                checks['Private storage provider reachable'] = False
        try:
            with connection.cursor() as cursor: cursor.execute('SELECT 1')
            checks['PostgreSQL reachable'] = connection.vendor=='postgresql'
            executor=MigrationExecutor(connection)
            checks['All migrations applied'] = not executor.migration_plan(executor.loader.graph.leaf_nodes())
            checks['Named Super Admin has verified Google login'] = GOOGLE_IDENTITY.objects.filter(verified_email=INITIAL_SUPERADMIN,user__is_superuser=True,user__is_active=True).exists()
        except Exception:
            checks['Database/schema readiness'] = False
        for label,ok in checks.items(): self.stdout.write(('PASS ' if ok else 'BLOCKED ')+label)
        self.stdout.write('Manual gates: provider secret rotation, Google/Workspace MFA policy, backup+restore exercise, host/proxy monitoring, and authorized acceptance/penetration testing.')
        if not all(checks.values()): raise CommandError('Not ready to publish. Resolve BLOCKED checks; no changes were made.')
