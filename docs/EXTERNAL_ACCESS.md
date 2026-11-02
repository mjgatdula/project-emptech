# Direct Google registration — current policy

Updated 2 November 2026. The owner revised the policy: TIP and external Gmail/Google Workspace accounts register and log in DIRECTLY. Super Admin approval is NOT required. This document supersedes the earlier invitation workflow.

## Behavior

The existing Google button creates an ordinary account after validating Google's signature, issuer, audience, authorized party, expiry, nonce and verified email. Google must be authoritative for the email (Gmail or a matching Workspace hosted domain). TIP accounts still require the tip.edu.ph Workspace claim. No client privilege fields are trusted. Password registration remains disabled in production.

TIP users retain school roles and the approved initial staff roster. External users are ordinary guest/External user accounts: they can use existing ordinary report/claim flows but cannot access staff administration, OSA operations or unrelated private evidence. They cannot submit school student identity details or receive staff roles/campus assignments. No invitation, invitation email, approval expiry, new secret or Google-origin change is required.

Super Admin can manage account activation through existing Accounts & permissions. Deactivating an external account blocks login, access tokens and refresh. Existing email-only accounts are never silently merged with a Google identity; conflicts still require ownership review.

## Retired invitation workflow

The approval panel is removed from Administration. Existing EXTERNAL_ACCESS records, audit history and applied migration 0008 remain preserved. They no longer gate registration or token use. The old Super-Admin-only endpoint permits historical GET reads but returns HTTP 410 for POST/PATCH. Old invitation revocation/expiry does not disable a public-registration account; use account activation instead. The old unmounted ExternalInvitations component is not included in the active UI bundle. No destructive schema migration was performed.

## Verification

24 focused signed-Google/JWT/authorization checks passed: Gmail registration without any approval, external Workspace registration, TIP registration, ordinary roles, ignored privilege injection, valid access/refresh, inactive account denial, no email-only takeover, no external staff promotion, and retired invitation writes. Fixture writes were rolled back; no real external account was created. Full frontend lint/build and Django configuration/migration drift checks passed. Actual Google login on the live site remains to be verified after deploying the updated source. These checks are not a penetration-test certification.

## Deploy the small update

The prepared PROJ/TIPPED-DIRECT-UPDATE folder contains 11 changed files under backend, frontend and docs. Upload those THREE child folders together at the GitHub repository root, commit and manually deploy latest commit on Render. Do not upload the parent folder. No environment changes or database migration is required. The full release ZIP is also refreshed. After Render is Live, hard-refresh the site and directly sign in with an external Gmail in an Incognito window. No approval step should appear.

Runtime files changed: backend/base/google_auth.py, access_policy.py, authentication.py, external_access.py; frontend/src/components/GoogleSignIn.jsx; frontend/src/pages/Administration.jsx, Login.jsx, Register.jsx. Docs and project context updated. Existing report/claim permissions and pages/components/context organization are retained.
