# Google authentication and Docker release status

Updated 2 November 2026. This document supersedes older handoff snapshots for authentication and release status.

## Implemented

The website uses real Google Identity Services and server-verified Google ID tokens, then issues the existing application access/refresh JWT pair. Verified tip.edu.ph Google Workspace identities register directly; verified external Gmail/Workspace identities now register directly without approval; see EXTERNAL_ACCESS.md. Google provides identity only: no Gmail/Drive access and no client secret is required. Tokens are validated for signature, issuer, audience, expiry, nonce and authorized party. A session-bound, single-use challenge prevents replay. Google identity is keyed by immutable subject, not client-supplied privileges or email alone. Existing accounts require an authenticated explicit link; an email match never silently grants access.

Local password authentication defaults to disabled; production fixes it disabled. SchoolJWTAuthentication also rejects existing tokens from accounts without a matching school Google identity. A stored token or localStorage user object alone grants no permissions. Access/refresh JWTs remain in the current frontend storage design; Django admin uses a separate fresh Google-confirmed session. Superuser Django admin proof lasts 15 minutes; signing in through Google again renews it. Google Workspace identity is separate from student-profile approval.

First verified Google linking provisions the designated owner mjgatdula@tip.edu.ph as Super Admin and the five approved emails in base/deployment_policy.py as Admin. Provisioning is not repeated on every login, preserving later demotions. Admin manages ordinary accounts/catalogue; OSA is a separate campus-scoped operational assignment; only Super Admin assigns privileged roles. No OSA personnel were invented or assigned. The owner successfully signed in with Google and the linked active Superuser identity was verified in PostgreSQL.

Public Google Client ID: 117583489985-mogcbg4lo07a3n3r7rof6qth2durdaeg.apps.googleusercontent.com

Authorized development origins: http://localhost:5174 and http://127.0.0.1:5174. The public HTTPS origin must be added after hosting is chosen. Confirm Google's audience/publishing restrictions for the intended school users. This integration uses the JS credential callback, not a redirect authorization-code flow.

## Schema and cleanup

Applied migration 0006 adds GOOGLE_IDENTITY (one-to-one User, unique subject, verified email, linked timestamp). Applied 0007 creates tipped_shared_cache for shared production throttles. Core ERD business relationships are unchanged; document the additional identity table as an authentication extension.

Only the approved disposable accounts ja@gmail.com and ja2@gmail.com were removed, with their 3 reports, 1 claim and related notifications. No private uploaded files belonged to them. Other accounts/catalogue were preserved. Recovery archive is Windows DPAPI encrypted under the original Windows account at C:/Users/Jarren/.codex/backups/tipped/test-cleanup-20261101T144725141160.dpapi. Recovery archive decryption and expected user/report counts were verified in memory; it must not be included in release artifacts. Keep that Windows account/profile available for recovery.

## Changed files

Backend: base/deployment_policy.py, models.py, google_auth.py, authentication.py, api.py, admin.py, health.py, urls.py; migrations/0006_google_identity.py and 0007_shared_cache.py; management/commands/deployment_readiness.py and purge_test_data.py; backend/settings.py and production_settings.py; requirements.txt; .env.example.

Frontend: components/GoogleSignIn.jsx; data/api.js; pages/Login.jsx, Register.jsx, Profile.jsx, Administration.jsx. Existing pages/components/context structure is retained. Campus Edit now scrolls/focuses the populated editor and indicates the selected record; it does not save until Save configuration is submitted.

Release: Dockerfile, docs/GOOGLE_SIGN_IN_DEPLOYMENT.md, context/project-overview.md and artifacts/tipped-docker-release.zip. Local credential-bearing settings.py is excluded from the release and Docker build.

## Verification

Earlier focused verification passed 76 Google/auth checks and 9 fresh-admin-proof/shared-cache checks; isolated fixture writes were rolled back. Final checks passed 9 JWT/owner/cleanup/recovery checks, including unlinked-token rejection, linked-token acceptance and inactive-user rejection. Django system checks, migration drift check, pip check, full frontend lint and production build passed. Actual browser administration and Arlegui Edit rendered correctly. A local outage was traced to stopped frontend/backend listeners; restarting both restored the page. This is not a claim that a penetration test or production deployment has passed.

## Docker preparation (PowerShell)

Docker is not installed in the current environment, so the image has NOT been built or run here. No hosting, billing or purchase was activated. Unzip the clean release and install Docker Desktop yourself if needed. From the release root:

```powershell
docker build -t tipped:release .
```

Create an untracked release.env using backend/.env.example as the key reference. Supply real production values for DJANGO_SECRET_KEY, JWT_SIGNING_KEY (different strong keys), DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, DB_PORT, DB_SSLMODE, GOOGLE_CLIENT_ID, DJANGO_ALLOWED_HOSTS, DJANGO_CSRF_TRUSTED_ORIGINS, PRIVATE_MEDIA_ROOT=/data/private_media, TRUST_PROXY_HEADERS=true and TRUSTED_PROXY_IP (actual controlled HTTPS reverse proxy). Never put secrets into the image or commit release.env. Production settings do not read a .env file automatically; Docker --env-file injects variables. ALLOW_PASSWORD_AUTH stays false.

With the database configured and private storage initialized, run the explicit release migration once, then the read-only readiness command:

```powershell
docker volume create tipped-private-media
docker run --rm --env-file release.env -v tipped-private-media:/data/private_media tipped:release python manage.py migrate --noinput
docker run --rm --env-file release.env -v tipped-private-media:/data/private_media tipped:release python manage.py deployment_readiness
docker run --name tipped --env-file release.env -p 127.0.0.1:8000:8000 -v tipped-private-media:/data/private_media tipped:release
```

The final command needs an actual trusted HTTPS reverse proxy; configure the chosen host's network and proxy IP accordingly. Production requires HTTPS and will redirect plain HTTP. The container runs as a non-root user: ensure persistent storage is writable by that user. The Docker TCP health check verifies process availability; monitor /api/health/ready/ via the actual HTTPS domain for database readiness. Back up PostgreSQL AND the private-media volume and prove restoration before launch.

## Owner-dependent launch gates

Choose hosting/domain, add its exact HTTPS Google origin, configure HTTPS/proxy/secrets/persistent volume, build and run the image, rotate previously exposed database credentials, complete real backup/restore, assign actual Admin/OSA accounts as needed, confirm school eligibility and Google app audience, enforce MFA/2-Step Verification on privileged Google accounts, and perform authorized penetration testing on a controlled deployment. Email/password reset delivery is not used in Google-only mode; account recovery follows Google/school policy. Application-level independent MFA is not implemented. Do not advertise the site as penetration-tested until testing is complete.

External-account extension: see [EXTERNAL_ACCESS.md](EXTERNAL_ACCESS.md). Applied additive migration 0008; no changes to initial TIP staff email roster. External accounts now register directly; account activation and ordinary-only privileges are rechecked on authenticated requests. Earlier invitation requirements are retired.
