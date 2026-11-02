"""Owner-approved initial roles. Applied only after verified Google ownership."""
SCHOOL_DOMAIN = 'tip.edu.ph'
INITIAL_SUPERADMIN = 'mjgatdula@tip.edu.ph'
INITIAL_ADMINS = frozenset({
    'mxhguevara@tip.edu.ph', 'mjmadornado@tip.edu.ph', 'mjldejesus@tip.edu.ph',
    'maavalenzuela@tip.edu.ph', 'mrlbcabanog@tip.edu.ph',
})
RESERVED_EMAILS = INITIAL_ADMINS | {INITIAL_SUPERADMIN}
