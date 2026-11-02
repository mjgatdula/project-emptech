# Current free rollout

Read [FREE_HOSTING_ROLLOUT.md](FREE_HOSTING_ROLLOUT.md) first. Owner approved Render Free + private Supabase storage with Aiven retained. This supersedes older missing-Google/cache/eligibility statements. Actual hosting/restore/MFA/rotation remain pending owner/provider steps.

# TIPPED production deployment

Updated 1 November 2026. Production configuration is prepared and checked, but the application has not been published to an external host. Choose a host that supports a Python/container web service, TLS reverse proxy, outbound PostgreSQL and persistent private storage.

## Deployment design

Browser -> HTTPS reverse proxy -> Waitress/Django on internal port 8000. WhiteNoise serves the built React assets and Django/React route fallback serves deep links. `/api/` and `/admin/` remain Django routes. Aiven PostgreSQL holds records; a persistent private volume holds photos/proofs. Private uploads are streamed through authorized API endpoints, not exposed by a public media route.

The Docker build has a Node 24 stage for `npm ci`/`npm run build` and a Python 3.14 stage for Django/Waitress. It runs as a non-root user. `backend/backend/settings.py`, actual `.env` files, local dependencies and uploads are excluded from the build context. Production never imports the credential-bearing local settings module.

## Environment variables

`backend/.env.example` lists placeholder values. It is not a live configuration and is not loaded automatically by Django. Supply actual environment variables through the hosting secret manager or a private ignored env file passed with Docker `--env-file`. Never paste secret values into chat, source control or build logs.

| Key | Purpose |
|---|---|
| DJANGO_SETTINGS_MODULE | `backend.production_settings` (set by Docker image) |
| DJANGO_SECRET_KEY | Long random production Django signing secret |
| JWT_SIGNING_KEY | Independent long random JWT signing secret |
| DJANGO_ALLOWED_HOSTS | Comma-separated actual public hostnames; no URL scheme |
| DJANGO_CSRF_TRUSTED_ORIGINS | Comma-separated complete HTTPS origins for unsafe account requests |
| DB_HOST, DB_PORT | Actual Aiven PostgreSQL host and service port; do not assume 5432 |
| DB_NAME, DB_USER, DB_PASSWORD | Actual database name/user/password, separate from Django website accounts |
| DB_SSLMODE | TLS mode, defaults to require; use provider CA/verify-full if configuring certificate verification |
| PRIVATE_MEDIA_ROOT | Persistent upload path; Docker uses `/data/private_media` |
| TRUSTED_PROXY_IP | Actual trusted HTTPS reverse proxy address required by the Docker startup command |
| TRUST_PROXY_HEADERS | Optional Django forwarded-proto trust; enable only for the configured trusted proxy |

Use a single public origin for frontend and API. No CORS package is needed for that arrangement. Do not point the production frontend at a private development address. `VITE_API_BASE_URL`, if used, is a public build-time base origin, not a secret; the client appends `/api` itself. Cross-origin cookies/CORS would need separate deliberate configuration and are not the default deployment.

## Windows PowerShell container preparation

Prerequisites: Docker installed and running, actual hosting/domain/proxy configuration, and privately supplied environment values. Docker is not installed/configured in the current workspace, so these container commands are documented rather than executed.

```powershell
Set-Location 'C:\Users\Jarren\Downloads\PROJ\EMTECH2_TIPPED_FINAL'
# Create a private ignored file, then populate its placeholders locally.
Copy-Item -LiteralPath backend\.env.example -Destination backend\.env.production
# Edit backend/.env.production privately. Do not deploy with placeholder values.
docker build -t tipped .
# Apply migrations once as a release operation, not from every web instance.
docker run --rm --env-file backend/.env.production tipped python manage.py migrate
docker run --rm --env-file backend/.env.production tipped python manage.py bootstrap_catalogue
docker run --rm --env-file backend/.env.production tipped python manage.py bootstrap_roles
# The designated owner signs in with verified school Google identity; do not create password-only administrators.
```

Create a persistent volume with appropriate non-root ownership for `/data/private_media`. The service user in the image is `tipped`; the mount must be writable by that user and must survive replacement of the container. An orchestrator-managed disk/bind mount must be prepared with those permissions; do not solve permission errors by making evidence public or running the web service as root.

A host-specific launch example after volume and proxy preparation:

```powershell
docker volume create tipped-private-media
docker run -d --name tipped --env-file backend/.env.production -p 127.0.0.1:8000:8000 --mount source=tipped-private-media,target=/data/private_media tipped
```

Docker named-volume initialization can copy the image directory's ownership into an empty volume; verify write access under the non-root service user on the chosen host. The example binds to the host loopback because a local reverse proxy is expected. Container-to-container proxies need the appropriate private Docker network instead. Set TRUSTED_PROXY_IP to the address Waitress actually observes for that proxy, not a guessed public address. The proxy must preserve the intended Host and set X-Forwarded-Proto from the real client TLS scheme. Prevent direct public access to port 8000 and strip spoofed forwarded headers at the proxy.

Waitress only trusts forwarded scheme from the specified proxy. HTTPS redirects, secure cookies and HSTS are enforced by Django. An incorrect proxy address/scheme setup can cause redirect loops; fix the proxy trust instead of disabling production HTTPS protections. The body limit is 20 MB; retain compatible upload limits at the reverse proxy.

## Without containers

Build `frontend/dist` with npm, install `backend/requirements.txt`, and supply all production environment variables in the process. From `backend`, run:

```powershell
# Production environment values must already be set in this terminal/service.
$env:DJANGO_SETTINGS_MODULE = 'backend.production_settings'
..\venv\Scripts\python.exe -B manage.py check --deploy
..\venv\Scripts\python.exe -B manage.py migrate
..\venv\Scripts\python.exe -B manage.py collectstatic --noinput
..\venv\Scripts\waitress-serve.exe --listen=127.0.0.1:8000 --max-request-body-size=20971520 --trusted-proxy=$env:TRUSTED_PROXY_IP --trusted-proxy-headers=x-forwarded-proto backend.wsgi:application
```

Run behind the same configured HTTPS reverse proxy and use persistent PRIVATE_MEDIA_ROOT. `runserver` and Vite's development/preview server are not production hosting. The frontend's Google Fonts request may fall back to the CSS font stack when external font delivery is unavailable.

## Operations and acceptance

- Verify an actual normal account can report an item, staff at that campus can approve/receive it, another user can claim, and authorized staff can verify then physically release. Test wrong-campus access with real authorized acceptance accounts; do not distribute administrator credentials.
- Review campus/program/category/office configuration and explicitly assign trusted OSA accounts. Normal registration creates an active ordinary user. Student profile review remains separate from Google school identity verification; the accepted Google domain is tip.edu.ph. Confirm institutional approval and student eligibility policy before school rollout.
- Preserve PostgreSQL migrations. Existing migration 0003 refuses a nonempty legacy integer-key report table rather than guessing data conversion. Back up before migration/release. Do not drop tables or use --fake as a repair shortcut.
- Back up and restore both Aiven data and private file storage. Database-only backups cannot restore images/proof files. Apply an institutional retention policy to evidence, audit history and exports.
- Schedule `python manage.py flushexpiredtokens` daily using the production environment. It removes expired JWT bookkeeping, not active accounts.
- Production throttles use the shared database cache. Verify deployed trusted client-IP handling before horizontally scaling; a reverse-proxy account rate limit can provide an additional deployment control. Do not trust arbitrary forwarded client IP headers.
- PDF/image validation does not provide antivirus scanning. Add a private upload scanning service if required by institutional policy; never send student evidence to a third party without the proper authorization.
- Local settings.py still contains the existing local configuration by owner preference. Ignore rules do not untrack an already committed file. Before publishing a repository, review tracked files/history and replace any previously exposed credentials through the service owner; changing a file alone does not revoke a leaked secret. No secret/password rotation was performed during this implementation.
- Google school sign-in and server-side identity verification are implemented. Native password authentication defaults off; recovery follows Google/school policy. Independent SMTP/password-reset and push delivery are not implemented. See the current rollout document.

## What was verified here

Django `check --deploy` passed with the separate production settings and process-only credentials. Static collection, built React deep links, built JavaScript delivery, API root, HTTPS redirect and denial of public private-media URLs passed. Waitress accepted the trusted-proxy/body-size options. The production image was not built and no public service/domain was deployed. Those final host-specific checks require Docker/hosting to be available.

Role provisioning: run manage.py bootstrap_roles after migrate. It creates only empty TIPPED Administrators and TIPPED OSA groups, without generic model permissions or user membership. Only the Superuser assigns actual roles/campus scope through the React Administration page. /admin/ is Superuser-only in both local and production URL configurations.

Local development connection handling uses CONN_MAX_AGE=0 after a confirmed thread-related connection buildup; see DATABASE_CONNECTION_FIX.md. Do not copy production persistent-connection settings into threaded runserver. Production still requires a bounded total worker/instance connection budget within Aiven capacity.
