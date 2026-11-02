# Free hosting rollout — current status and operator steps

Updated 2 November 2026. Owner approved Render Free + Supabase Free PRIVATE object storage; Aiven remains the application database. OSA email/campus assignments are pending. No paid plan, billing, external repository publication or public deployment has been activated by the agent.

## Implemented locally

- render.yaml declares one FREE Docker web service, no Render database/disk and no automatic deployments. Render builds Docker remotely, so local Docker Desktop is not required for hosting. The assigned HTTPS onrender.com address avoids buying a domain.
- backend/render_start.py is Render-only, binds the provider PORT and uses HTTPS WSGI scheme because Render redirects HTTP and terminates TLS at its edge. It does not trust client-supplied forwarded headers. Startup runs collectstatic and deployment_readiness and refuses failed security/storage/database/owner checks; it does not auto-migrate production on every boot.
- Optional private S3-compatible storage uses django-storages/boto3. All report images and claim evidence retain their authorized Django streaming endpoints. No public object URL or ACL is issued. Local development retains its existing private filesystem storage. On Render, startup rejects filesystem storage to prevent silent upload loss.
- Storage timeout/retry limits, non-overwriting names and the existing upload-validation/permission rules remain active. No ERD field or migration change was needed.
- export_private_media downloads referenced files with SHA256/size manifests and refuses overwriting an existing backup directory. It supports the local and remote storage backend.
- scripts/backup-production.ps1 prepares a PostgreSQL 18 custom dump plus private file checkpoint. It requires acknowledgement that all writers are paused, protects the new Windows backup directory and avoids printing credentials.
- scripts/verify-restore.ps1 restores only into a disposable Docker PostgreSQL container with no published ports and no network, checks six critical-table counts plus dump/media hashes, then removes that disposable container. It never points restore at Aiven or production.

## Checks already performed

15 targeted storage/backup/security checks passed: local fallback preserved, private remote URL denied, no public ACL, overwrite disabled, expected SDK upload request, anonymous staff/profile/configuration denied, GET logout rejected, direct private-media URL denied, forged JWT denied, exported file hash verified and backup overwrite rejected. The SDK provider was stubbed; no student file was uploaded externally during these checks. Django system and production security configuration checks passed, migration drift was zero, pip dependencies passed. PowerShell backup/restore syntax passed.

Actual cloud upload/download/privacy tests, Docker build/run, native PostgreSQL restore exercise, provider credential rotation, Google MFA verification, actual host proxy/rate-limit behavior and public deployment penetration testing have NOT happened. Prepared scripts are not evidence that the backup restore has passed.

## Owner actions, in order

1. Sign in/create FREE Render and Supabase accounts and personally accept their terms. If either asks for a paid plan/payment method, stop; no payment is authorized. Create a separate Free TIPPED Supabase project. Its database password is provider setup only; it does not replace Aiven database credentials.
2. In Supabase Storage, create bucket tipped-private with Public OFF. Obtain the exact S3 endpoint, project region and S3 server credentials from its dashboard. Keep S3 keys server-only. These keys can bypass storage policies and must never appear in frontend code, VITE variables, a public repository, logs or chat. Use a project dedicated to TIPPED.
3. Put the clean release ZIP into a NEW PRIVATE Git repository that you own and connect that repository to Render. Do not push the original working repository/history: it may contain historical credentials. The ZIP excludes local settings.py, actual env files, uploads, backups, dependencies and Git history.
4. Import render.yaml or create a FREE Docker Web Service using its Docker command python render_start.py. Aiven is external; do not create a Render Postgres database. Render automatically supplies RENDER_EXTERNAL_HOSTNAME. Production settings validate and add that exact hostname and HTTPS CSRF origin; omit the manual DJANGO_ALLOWED_HOSTS and DJANGO_CSRF_TRUSTED_ORIGINS rows during Render creation. Explicit custom-domain values remain supported; non-Render deployments still require DJANGO_ALLOWED_HOSTS. Supply DB_* values from Aiven and PRIVATE_STORAGE_* values from Supabase privately in Render Environment. DJANGO_SECRET_KEY and JWT_SIGNING_KEY must be independent random secrets of at least 50 characters. Generate privately with Python secrets.token_urlsafe(64), twice; do not share the output in chat. Supply GOOGLE_CLIENT_ID from GOOGLE_SIGN_IN_DEPLOYMENT.md. ALLOW_PASSWORD_AUTH stays false. Never expose port 8000 separately.
5. Review the concrete service/repository/environment configuration before the first public deployment. The initial build/run remains pending provider account access. For future migrations, run an explicit controlled release migration against the intended database before changing the running app. Current Aiven migrations are already applied and the new storage configuration needs no migration.
6. Add the actual HTTPS onrender.com origin to the existing Google OAuth Web Client's Authorized JavaScript origins. Keep localhost origins for development. Do not add a client secret to the frontend. Confirm Google audience/testing restrictions permit the intended school accounts. Personally sign in to verify the production flow; keep passwords, credentials and tokens private.
7. Test a real approved image upload, restart/redeploy the web container and verify it survives. Verify an unauthorized user cannot download claim evidence, direct unsigned storage URLs do not expose objects, and correct-campus OSA can access only authorized files. Existing local uploads are NOT automatically copied to the new bucket: export and transfer referenced objects with the same keys before switching storage. Current file export and provider transfer must be verified; do not discard local originals.
8. Check actual Render client-IP/proxy behavior with spoofed headers before campus rollout. Current throttles deliberately use the socket peer and do not trust arbitrary X-Forwarded-For. A shared proxy can aggregate anonymous/login limits; configure verified proxy behavior only after observing the deployed ingress, rather than blindly trusting spoofable headers.

## Credentials and MFA — owner-only actions

Aiven: open the PostgreSQL service, Users, select the application database user and reset its password yourself. Update the new value privately in Render DB_PASSWORD, your local settings.py database PASSWORD and the private production env file used for backups. Restart affected app processes and verify /api/health/ready/ returns 200. Do not paste the password into chat. Rotation has NOT been performed merely by changing source code. Confirm Aiven's current service plan is actually free: the previous console showed a trial, and free web/storage hosting does not guarantee the existing database is free.

Google: https://myaccount.google.com/security → 2-Step Verification. The owner and each privileged Admin/OSA account must complete their own enrollment; use school IT if institutional policy controls it. Store recovery codes privately. A verified Google ID token does not itself prove MFA was performed. This application does not independently enforce a TOTP/MFA enrollment claim or enable MFA on someone else's account. Confirm the privileged-account policy before claiming MFA enforcement.

Admin status: all five approved Admin emails were still pending verified Google login at the latest read-only check (0 linked). Existing first-link policy grants only their approved Admin role after actual Google ownership verification. The designated owner already has verified Google Superuser access. OSA remains unassigned until actual personnel emails and campus scopes are provided. Do not invent OSA accounts or reuse student identities as staff.

## Backup and restore operation (not yet executed)

Docker is required locally for the PostgreSQL 18 backup client and isolated restore exercise. Install/start Docker Desktop yourself and review its terms; no purchase is required by these scripts. Alternatively, run equivalent pg_dump/pg_restore on an approved PostgreSQL 18 operator machine. The live server was verified as PostgreSQL major 18.

Create backend/.env.production privately from backend/.env.example and populate real production values. The file is ignored; do not commit it. Pause ALL writers to the target database and uploads (both local and hosted app), then run from the project root:

```powershell
$backupPath = Join-Path $env:USERPROFILE ('.codex/backups/tipped-production/' + (Get-Date -Format yyyyMMdd-HHmmss))
.\scripts\backup-production.ps1 -EnvFile .\backend\.env.production -Destination $backupPath -WritesPaused
.\scripts\verify-restore.ps1 -BackupDirectory $backupPath
```

Resume writers only after the checkpoint operation ends. Preserve a failed checkpoint for diagnosis, but do not count it as a complete backup. Store backups on protected encrypted storage and maintain an off-machine encrypted copy with institution-approved access; directory ACL protection is not encryption. Schedule recurring checkpoints on an approved operator machine and document retention. A restore-count/hash pass is a recovery baseline; also perform a functional report/claim/file-read check in an isolated application connected to the restored database before final acceptance.

## Penetration-test handoff

The classmate needs an explicitly authorized staging URL and scope, disposable test accounts for Student/Admin/OSA on two campuses, and a private findings channel. Test cross-account/cross-campus object access, role changes, private images/evidence, expired/forged/replayed tokens, CSRF, upload validation, XSS, injection, claim/release rules and notification privacy. Recheck throttles and proxy headers. No denial-of-service/load attack or attack on Google/Aiven/Supabase infrastructure is authorized by this document. Use provider rules and a controlled test window. Resolve actual findings and rerun the affected checks before public launch. No zero-bug or penetration-test certification is claimed.

## Current changed-file manifest

backend/base/models.py; backend/base/private_storage.py; backend/base/management/commands/deployment_readiness.py and export_private_media.py; backend/backend/production_settings.py; backend/render_start.py; backend/requirements.txt; backend/.env.example; render.yaml; scripts/backup-production.ps1; scripts/verify-restore.ps1; scripts/package_release.py; docs/DEPLOYMENT.md; docs/FREE_HOSTING_ROLLOUT.md; context/project-overview.md; artifacts/tipped-docker-release.zip. Previous Login.jsx/GoogleSignIn.jsx visual adjustments are included in the refreshed release.

Official references: https://render.com/docs/free ; https://render.com/docs/tls ; https://render.com/docs/blueprint-spec ; https://supabase.com/docs/guides/storage/s3/authentication ; https://django-storages.readthedocs.io/en/latest/backends/amazon-S3.html ; https://www.postgresql.org/docs/current/app-pgdump.html .

Render hostname follow-up: production settings now derive the exact host/HTTPS CSRF origin from the provider environment, validated to a single onrender.com hostname. No wildcard or request-header inference is used. The two manual hostname Blueprint prompts were removed. Upload the refreshed deployment source before relying on this behavior; editing local files does not update GitHub main.
