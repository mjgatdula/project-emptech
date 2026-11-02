"""Render-only HTTPS ingress. Does not trust client-supplied forwarded headers."""
import os
import subprocess
import sys

if os.environ.get('RENDER') != 'true':
    raise SystemExit('This entry point is only for Render HTTPS ingress.')
os.environ['DJANGO_SETTINGS_MODULE'] = 'backend.production_settings'
# Render redirects HTTP at the edge; the internal listener is not published directly.
os.environ['TRUST_PROXY_HEADERS'] = 'false'
subprocess.run([sys.executable, 'manage.py', 'collectstatic', '--noinput'], check=True)
subprocess.run([sys.executable, 'manage.py', 'deployment_readiness'], check=True)
from backend.wsgi import application
from waitress import serve

serve(application, host='0.0.0.0', port=int(os.environ.get('PORT', '10000')),
      url_scheme='https', threads=4, connection_limit=100,
      max_request_body_size=20 * 1024 * 1024)
