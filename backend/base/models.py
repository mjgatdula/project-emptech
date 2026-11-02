import uuid

from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.db import models
from django.utils import timezone


class PrivateEvidenceStorage(FileSystemStorage):
    """Evidence stays outside public MEDIA_ROOT and has no public download URL."""

    def url(self, name):
        raise ValueError('Claim evidence requires an authorized download endpoint.')


def private_evidence_storage():
    if getattr(settings, 'PRIVATE_STORAGE_BACKEND', 'filesystem') == 's3':
        from .private_storage import PrivateObjectStorage
        from botocore.config import Config
        return PrivateObjectStorage(
            endpoint_url=settings.PRIVATE_STORAGE_ENDPOINT,
            access_key=settings.PRIVATE_STORAGE_ACCESS_KEY,
            secret_key=settings.PRIVATE_STORAGE_SECRET_KEY,
            bucket_name=settings.PRIVATE_STORAGE_BUCKET,
            region_name=settings.PRIVATE_STORAGE_REGION,
            max_memory_size=5 * 1024 * 1024,
            client_config=Config(signature_version='s3v4',
                s3={'addressing_style': 'path'}, connect_timeout=5, read_timeout=15,
                retries={'max_attempts': 2, 'mode': 'standard'},
                request_checksum_calculation='when_required',
                response_checksum_validation='when_required'),
        )
    return PrivateEvidenceStorage(
        location=getattr(settings, 'PRIVATE_MEDIA_ROOT', settings.BASE_DIR / 'private_media'),
    )


def external_access_expiry():
    from datetime import timedelta
    return timezone.now() + timedelta(days=30)


class EXTERNAL_ACCESS(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(max_length=254, unique=True)
    invited_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name='external_invitations_created')
    accepted_user = models.OneToOneField(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='external_access')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField(default=external_access_expiry)
    accepted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at', 'id']
        constraints = [models.UniqueConstraint(models.functions.Lower('email'), name='external_email_case_insensitive')]


class GOOGLE_IDENTITY(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, primary_key=True, on_delete=models.CASCADE, related_name='google_identity')
    subject = models.CharField(max_length=255, unique=True)
    verified_email = models.EmailField(max_length=254)
    linked_at = models.DateTimeField(default=timezone.now, editable=False)

    def __str__(self):
        return f'Google identity for account {self.user_id}'


class PROGRAM(models.Model):
    id = models.BigAutoField(primary_key=True)
    code = models.CharField(max_length=32, unique=True)
    name = models.CharField(max_length=150)

    def __str__(self):
        return f'{self.code} - {self.name}'


class SITE(models.Model):
    id = models.BigAutoField(primary_key=True)
    code = models.CharField(max_length=32, unique=True)
    name = models.CharField(max_length=150)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class CATEGORY(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=100, unique=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class STUDENT_PROFILE(models.Model):
    class ApprovalStatus(models.TextChoices):
        PENDING = 'pending', 'Pending'
        APPROVED = 'approved', 'Approved'
        REJECTED = 'rejected', 'Rejected'

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, primary_key=True, on_delete=models.CASCADE,
        related_name='student_profile',
    )
    full_name = models.CharField(max_length=255)
    student_number = models.CharField(max_length=50, unique=True)
    program = models.ForeignKey(PROGRAM, on_delete=models.PROTECT, related_name='students')
    site = models.ForeignKey(SITE, on_delete=models.PROTECT, related_name='students')
    approval_status = models.CharField(
        max_length=20, choices=ApprovalStatus.choices, default=ApprovalStatus.PENDING,
    )

    def __str__(self):
        return f'{self.student_number} - {self.full_name}'


class STAFF_SITE_ASSIGNMENT(models.Model):
    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='staff_site_assignments',
    )
    site = models.ForeignKey(SITE, on_delete=models.PROTECT, related_name='staff_assignments')
    permission_role = models.CharField(max_length=50)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['user', 'site'], name='unique_staff_site_assignment'),
        ]

    def __str__(self):
        return f'{self.user} - {self.site} ({self.permission_role})'


class OFFICE(models.Model):
    id = models.BigAutoField(primary_key=True)
    site = models.ForeignKey(SITE, on_delete=models.PROTECT, related_name='offices')
    name = models.CharField(max_length=150)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['site', 'name'], name='unique_office_name_per_site'),
        ]

    def __str__(self):
        return f'{self.site} - {self.name}'


class ITEM_REPORT(models.Model):
    class ReportType(models.TextChoices):
        LOST = 'lost', 'Lost'
        FOUND = 'found', 'Found'

    class PhotoVisibility(models.TextChoices):
        PENDING = 'pending', 'Pending review'
        APPROVED = 'approved', 'Approved for public display'
        HIDDEN = 'hidden', 'Hidden'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    reference_number = models.CharField(max_length=255, unique=True)
    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='item_reports',
    )
    site = models.ForeignKey(SITE, on_delete=models.PROTECT, related_name='item_reports')
    category = models.ForeignKey(CATEGORY, on_delete=models.PROTECT, related_name='item_reports')
    report_type = models.CharField(max_length=100, choices=ReportType.choices)
    title = models.CharField(max_length=100)
    description = models.TextField()
    location = models.CharField(max_length=255)
    # The incident date is entered by the reporter, not replaced by today's date.
    item_date = models.DateField(default=timezone.localdate)
    time = models.TimeField(null=True, blank=True)
    image = models.ImageField(upload_to='item_images/', storage=private_evidence_storage, blank=True, default='')
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)
    photo_visibility_status = models.CharField(
        max_length=20, choices=PhotoVisibility.choices, default=PhotoVisibility.PENDING,
    )
    photo_reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='reviewed_report_photos',
    )
    photo_reviewed_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField()

    def __str__(self):
        return f'{self.reference_number} - {self.title}'


class CUSTODY_RECEIPT(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    report = models.OneToOneField(
        ITEM_REPORT, on_delete=models.PROTECT, related_name='custody_receipt',
    )
    office = models.ForeignKey(OFFICE, on_delete=models.PROTECT, related_name='custody_receipts')
    received_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='recorded_custody_receipts',
    )
    private_identifying_notes = models.TextField(blank=True, default='')
    received_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f'Custody receipt for {self.report_id}'


class MODERATION_DECISION(models.Model):
    class Decision(models.TextChoices):
        PENDING = 'pending', 'Pending'
        APPROVED = 'approved', 'Approved'
        REJECTED = 'rejected', 'Rejected'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    report = models.ForeignKey(ITEM_REPORT, on_delete=models.PROTECT, related_name='moderation_decisions')
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='moderation_decisions',
    )
    decision = models.CharField(max_length=20, choices=Decision.choices)
    reason = models.TextField(blank=True, default='')
    decided_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f'{self.report_id} - {self.decision}'


class OWNERSHIP_CLAIM(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        VERIFIED = 'verified', 'Verified'
        REJECTED = 'rejected', 'Rejected'
        WITHDRAWN = 'withdrawn', 'Withdrawn'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    report = models.ForeignKey(ITEM_REPORT, on_delete=models.PROTECT, related_name='ownership_claims')
    claimant = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='ownership_claims',
    )
    private_explanation = models.TextField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='reviewed_ownership_claims',
    )
    reviewer_remarks = models.TextField(blank=True, default='')
    reviewed_at = models.DateTimeField(null=True, blank=True)
    submitted_at = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['report', 'claimant'], name='unique_claim_per_report_user'),
            models.UniqueConstraint(fields=['report'], condition=models.Q(status='verified'), name='one_verified_claim_per_report'),
        ]

    def __str__(self):
        return f'Claim {self.pk} for {self.report_id}'


class CLAIM_EVIDENCE(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    claim = models.ForeignKey(OWNERSHIP_CLAIM, on_delete=models.CASCADE, related_name='evidence')
    file = models.FileField(
        upload_to='claim_evidence/%Y/%m/', storage=private_evidence_storage, max_length=500,
    )

    def __str__(self):
        return f'Evidence {self.pk} for {self.claim_id}'


class RELEASE_RECORD(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    claim = models.OneToOneField(
        OWNERSHIP_CLAIM, on_delete=models.PROTECT, related_name='release_record',
    )
    released_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='release_records',
    )
    handover_location = models.CharField(max_length=255)
    released_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f'Release for claim {self.claim_id}'


class REPORT_CLOSURE(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    report = models.OneToOneField(ITEM_REPORT, on_delete=models.PROTECT, related_name='closure')
    closed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='report_closures',
    )
    reason = models.CharField(max_length=255)
    closed_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f'Closure for {self.report_id}'


class NOTIFICATION(models.Model):
    class Audience(models.TextChoices):
        PERSONAL = 'personal', 'Personal update'
        OPERATIONS = 'operations', 'OSA operational alert'

    audience = models.CharField(max_length=16, choices=Audience.choices, default=Audience.PERSONAL, db_default=Audience.PERSONAL)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    report = models.ForeignKey(ITEM_REPORT, null=True, blank=True, on_delete=models.SET_NULL, related_name='notifications')
    message = models.CharField(max_length=500)
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']


class AUDIT_EVENT(models.Model):
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name='audit_events')
    site = models.ForeignKey(SITE, null=True, on_delete=models.PROTECT, related_name='audit_events')
    report = models.ForeignKey(ITEM_REPORT, null=True, on_delete=models.SET_NULL, related_name='audit_events')
    action = models.CharField(max_length=60)
    reference = models.CharField(max_length=255, blank=True)
    detail = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        ordering = ['-created_at', '-id']
