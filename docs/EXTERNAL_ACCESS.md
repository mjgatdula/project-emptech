# TIP and invited external Google accounts

Implemented 2 November 2026. The source update is prepared; it must be committed to GitHub and manually deployed to Render before the live UI changes. Additive migration 0008_external_access is already applied to the existing Aiven database. Existing records and accounts were preserved. No real invitation, external test account or staff assignment was created.

## Policy and operation

Verified tip.edu.ph Google Workspace accounts can continue registering directly. Other users need an explicit active, unexpired approval for their exact email, created by the Super Admin. Supported external identities are Gmail or Google Workspace accounts for which Google is authoritative over the email. A non-Gmail third-party Google identity without the matching Workspace hosted-domain claim is rejected; a stale email_verified flag alone is not treated as current email ownership.

In the live app after deployment: Super Admin signs in → Profile → Administration → Accounts & permissions → External Google accounts. Enter the exact external email and access duration (1–365 days; default 30), then Approve or renew external email. The person then uses the existing Google button on Login/Register. No email is sent automatically and no password is created. The owner should notify the recipient directly. Google consent/audience or an organization's own Google policy may independently restrict sign-in.

External users are labelled guest/External user. They have existing ordinary report/claim capabilities: public reports and their own permitted records, not other users' private evidence or staff workflows. External users cannot create a school student profile or receive Administrator/OSA roles/campus assignments. They are not a separate invented staff identity. School staff provisioning remains exactly the approved TIP policy.

Approval binds to the verified application user on first acceptance. Google identity remains bound by immutable subject; existing email-only accounts are never silently merged. An existing conflicting account requires owner review, not an automatic takeover. A revoked or expired approval blocks subsequent Google login, JWT-authenticated requests and refreshes. Revoke access in the same Super Admin panel. Renewal reactivates the same approval and preserves its accepted-user binding; an inactive application account still cannot log in. All approval/acceptance/revocation actions create audit events.

## API and schema

GET /api/staff/external-access/: paginated results/count/page/pages/hasNext/hasPrevious; each result contains id, email, isActive, expiresAt, accepted, canSignIn. Super Admin only.

POST same endpoint: JSON email and optional days (default 30, range 1–365); creates or renews approval and returns 201 with message. TIP emails are rejected because they need no invitation. Case-normalized email and database/advisory locking prevent duplicate/racing identities. Approval alone never creates a User or privileges.

PATCH same endpoint: JSON id; revokes approval, returns message. There is no hard deletion or arbitrary account-role input.

The auth/config response additionally reports externalInvitationsEnabled. User responses additionally report isExternal and use guest as the ordinary external role. Existing isAdmin/isOsa/isSuperuser flags remain authoritative. Google signature, issuer, audience, azp, expiry, email verification, session-bound nonce and replay checks remain active. The frontend hosted-domain suggestion was removed so invited external people can select their Google account; backend eligibility remains enforced.

EXTERNAL_ACCESS: UUID primary key; unique case-insensitive email; nullable invited_by User FK; nullable accepted_user User one-to-one; is_active; created_at; expires_at; accepted_at. This is an additive authentication-policy table, not a replacement for Google identity or the lost/found ERD. Shared eligibility lives in access_policy.py with no HTTP/view imports. Revocation/privilege eligibility uses one query to avoid repeated remote database round trips.

## Verification

40 signed-Google/JWT/invitation/authorization checks passed, plus 6 optimized-policy query/revocation/privilege checks. They covered TIP login, invited Gmail/Workspace login, uninvited/unverified/unsupported identity rejection, forged privilege input, student/staff boundaries, approval renewal, expiry, revocation and refresh denial. Locally generated RSA signatures were actually validated against an isolated verification key; no real Google identity was impersonated. All test fixture writes were rolled back. Full frontend lint/build, Django checks and migration drift check passed. No retained test files were added to the project. Manual external login on the live host is pending source deployment and an actual owner-issued approval; no claim of zero bugs or completed penetration testing is made.

## Upload and deployment

Use artifacts/tipped-external-access-update.zip for a small update (20 files, below the GitHub web upload limit). Extract it into a fresh folder and drag its backend, frontend, docs and scripts folders together into GitHub Upload files at the repository root. Do not upload the parent folder or the ZIP itself. Commit, then Render → Manual Deploy → Deploy latest commit. No environment variable, secret value or Google authorized origin needs changing for this feature. The database migration is already applied to Aiven; do not reset tables or recreate accounts. Full tipped-docker-release.zip also includes the feature.

Changed runtime files: backend/base/{models,access_policy,external_access,google_auth,authentication,api,permissions,urls,views}.py; backend/base/migrations/0008_external_access.py; frontend/src/components/{ExternalInvitations,GoogleSignIn}.jsx; frontend/src/pages/{Administration,Login,Register,Profile}.jsx. Supporting docs, context and release packaging were updated. Existing pages/components/context organization is retained.
