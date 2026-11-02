"""Shared query scopes and workflow events. Identity always comes from JWT."""
from contextlib import contextmanager
import logging
from django.db.models import Exists, OuterRef, Subquery, Value
from django.db.models.functions import Coalesce
from django.utils import timezone
from .models import ITEM_REPORT, MODERATION_DECISION, CUSTODY_RECEIPT, RELEASE_RECORD, REPORT_CLOSURE, NOTIFICATION, AUDIT_EVENT
from .permissions import staff_sites, is_osa


def reports_query():
    latest = MODERATION_DECISION.objects.filter(report_id=OuterRef('pk')).order_by('-decided_at', '-pk')
    return ITEM_REPORT.objects.select_related('reporter', 'site', 'category').annotate(
        moderation_status=Coalesce(Subquery(latest.values('decision')[:1]), Value('pending')),
        has_custody=Exists(CUSTODY_RECEIPT.objects.filter(report_id=OuterRef('pk'))),
        is_closed=Exists(REPORT_CLOSURE.objects.filter(report_id=OuterRef('pk'))),
        is_released=Exists(RELEASE_RECORD.objects.filter(claim__report_id=OuterRef('pk'))),
    )


def public_reports():
    return reports_query().filter(moderation_status='approved', is_closed=False, expires_at__gt=timezone.now(), site__is_active=True, category__is_active=True)


def managed_reports(user):
    records = reports_query()
    if not is_osa(user):
        return records.none()
    return records if user.is_superuser else records.filter(site_id__in=staff_sites(user))


def event(actor, report, action, detail=''):
    return AUDIT_EVENT.objects.create(actor=actor, report=report, site_id=report.site_id, reference=report.reference_number, action=action, detail=detail[:500])


def notify(user, report, message, *, audience=NOTIFICATION.Audience.PERSONAL):
    NOTIFICATION.objects.create(user=user, report=report, message=message[:500], audience=audience)


def editable(report):
    return not report.is_closed and not report.has_custody and not report.ownership_claims.exists()


@contextmanager
def private_upload_scope():
    """Database rollback cannot undo storage writes; remove only new files on failure."""
    uploads = []
    try:
        yield uploads
    except Exception:
        for field in uploads:
            if field.name and field._committed:
                try:
                    field.storage.delete(field.name)
                except OSError:
                    logging.getLogger(__name__).error('Could not remove an uncommitted private upload.')
        raise


def visible_notifications(user):
    """Operational inbox history follows current OSA campus access; personal updates remain."""
    from django.db.models import Q
    return NOTIFICATION.objects.filter(user=user).filter(
        Q(audience=NOTIFICATION.Audience.PERSONAL) |
        Q(audience=NOTIFICATION.Audience.OPERATIONS,
          report_id__in=managed_reports(user).values('pk')))
