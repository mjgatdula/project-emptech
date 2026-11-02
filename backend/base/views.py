"""DRF endpoints. Mutations use row locks; private details stay role scoped."""
import csv
import json
import io
import uuid
from pathlib import Path
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db import transaction
from django.db.models import Q, Count
from django.http import FileResponse, HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import ValidationError, PermissionDenied, NotAuthenticated, NotFound
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response as DRFResponse
from rest_framework import serializers
from .models import (ITEM_REPORT, SITE, CATEGORY, PROGRAM, OFFICE, STUDENT_PROFILE, STAFF_SITE_ASSIGNMENT,
    MODERATION_DECISION, CUSTODY_RECEIPT, OWNERSHIP_CLAIM, CLAIM_EVIDENCE, RELEASE_RECORD,
    REPORT_CLOSURE, NOTIFICATION, AUDIT_EVENT)
from .permissions import (can_manage, require_manager, staff_sites, IsCampusStaff,
    IsAccountAdministrator, is_privileged_account, ordinary_accounts, ADMIN_GROUP, OSA_GROUP)
from .services import reports_query, public_reports, managed_reports, event, notify, editable, private_upload_scope, visible_notifications
from .serializers import ReportSerializer, ReportWriteSerializer, ClaimWriteSerializer
from .api import user_data


class Response(DRFResponse):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self['Cache-Control'] = 'private, no-store'


class Pagination(PageNumberPagination):
    page_size = 12
    page_size_query_param = 'page_size'
    max_page_size = 50


def page_response(records, request, serialize):
    paginator = Pagination()
    page = paginator.paginate_queryset(records, request)
    return Response({'results': serialize(page), 'count': paginator.page.paginator.count,
        'page': paginator.page.number, 'pages': paginator.page.paginator.num_pages,
        'hasNext': paginator.page.has_next(), 'hasPrevious': paginator.page.has_previous()})


def report_data(report, request):
    return ReportSerializer(report, context={'request': request}).data


def filters(records, params):
    if params.get('q'):
        q = params['q'][:255]
        records = records.filter(Q(title__icontains=q) | Q(description__icontains=q) | Q(location__icontains=q) | Q(reference_number__icontains=q))
    if params.get('type'):
        if params['type'] not in {'lost', 'found'}:
            raise ValidationError('Choose lost or found.')
        records = records.filter(report_type=params['type'])
    for key in ['site', 'category']:
        if params.get(key):
            value = serializers.IntegerField(min_value=1, max_value=9223372036854775807).run_validation(params[key])
            records = records.filter(**{f'{key}_id': value})
    dates = {}
    for key, lookup in [('from', 'item_date__gte'), ('to', 'item_date__lte')]:
        if params.get(key):
            dates[key] = serializers.DateField().run_validation(params[key])
            records = records.filter(**{lookup: dates[key]})
    if dates.get('from') and dates.get('to') and dates['from'] > dates['to']:
        raise ValidationError('The end date must be on or after the start date.')
    return records.order_by('-created_at', '-pk')


def visible_report(request, pk):
    report = get_object_or_404(reports_query(), pk=pk)
    public = report.moderation_status == 'approved' and not report.is_closed and report.expires_at > timezone.now() and report.site.is_active and report.category.is_active
    prior_claim = not public and request.user.is_authenticated and report.ownership_claims.filter(claimant=request.user).exists()
    if not public and not prior_claim and request.user.pk != report.reporter_id and not can_manage(request.user, report):
        raise NotFound('This report is not publicly available.')
    return report


def notify_staff(report, message):
    User = get_user_model()
    ids = STAFF_SITE_ASSIGNMENT.objects.filter(site_id=report.site_id, is_active=True, site__is_active=True).values_list('user_id', flat=True)
    for staff in User.objects.filter(is_active=True).filter(Q(is_superuser=True) | Q(groups__name=OSA_GROUP, pk__in=ids)).distinct():
        if staff.pk != report.reporter_id:
            notify(staff, report, message, audience=NOTIFICATION.Audience.OPERATIONS)


@api_view(['GET'])
@permission_classes([AllowAny])
def catalogue(request):
    def rows(model, fields):
        return list(model.objects.filter(is_active=True).order_by('name').values(*fields))
    return Response({'sites': rows(SITE, ['id', 'code', 'name']), 'categories': rows(CATEGORY, ['id', 'name']),
        'programs': list(PROGRAM.objects.order_by('name').values('id', 'code', 'name')),
        'offices': rows(OFFICE, ['id', 'site_id', 'name'])})


@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def report_list(request):
    if request.method == 'GET':
        if request.query_params.get('scope') == 'mine':
            if not request.user.is_authenticated:
                raise NotAuthenticated()
            records = reports_query().filter(reporter=request.user)
        else:
            records = public_reports()
        return page_response(filters(records, request.query_params), request, lambda rows: ReportSerializer(rows, many=True, context={'request': request}).data)
    if not request.user.is_authenticated:
        raise NotAuthenticated()
    serializer = ReportWriteSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    with private_upload_scope() as uploads, transaction.atomic():
        serializer.context['uploads'] = uploads
        report = serializer.save(reporter=request.user)
        event(request.user, report, 'report_created')
        notify(request.user, report, f'{report.reference_number} was submitted and is pending staff review.')
        notify_staff(report, f'New {report.report_type} report awaiting review: {report.reference_number}.')
    return Response({'report': report_data(reports_query().get(pk=report.pk), request)}, status=201)


@api_view(['GET', 'PATCH', 'DELETE'])
@permission_classes([AllowAny])
def report_detail(request, pk):
    if request.method != 'GET':
        if not request.user.is_authenticated:
            raise NotAuthenticated()
        with private_upload_scope() as uploads, transaction.atomic():
            get_object_or_404(ITEM_REPORT.objects.select_for_update(), pk=pk)
            report = reports_query().get(pk=pk)
            if report.reporter_id != request.user.pk or not editable(report):
                raise PermissionDenied('Only the reporter can change a report before custody or claims begin.')
            if request.method == 'DELETE':
                if report.moderation_decisions.exists():
                    raise ValidationError('Reports with review history must be closed rather than deleted.')
                event(request.user, report, 'report_deleted')
                storage, name = report.image.storage, report.image.name
                report.delete()
                if name:
                    transaction.on_commit(lambda: storage.delete(name), robust=True)
                return Response(status=204)
            serializer = ReportWriteSerializer(report, data=request.data, partial=True, context={'uploads': uploads})
            serializer.is_valid(raise_exception=True)
            old_name, storage = report.image.name, report.image.storage
            image_changed = 'image' in serializer.validated_data or serializer.validated_data.get('remove_image')
            report = serializer.save()
            if image_changed:
                report.photo_visibility_status = 'pending'
                report.photo_reviewed_by = None
                report.photo_reviewed_at = None
                report.save(update_fields=['photo_visibility_status', 'photo_reviewed_by', 'photo_reviewed_at'])
                if old_name and old_name != report.image.name:
                    transaction.on_commit(lambda: storage.delete(old_name), robust=True)
            MODERATION_DECISION.objects.create(report=report, reviewer=request.user, decision='pending', reason='Reporter updated the submission; staff review required.')
            event(request.user, report, 'report_updated')
            notify_staff(report, f'Updated report awaiting review: {report.reference_number}.')
    report = visible_report(request, pk)
    data = report_data(report, request)
    data['myClaim'] = report.ownership_claims.filter(claimant=request.user).values('id', 'status').first() if request.user.is_authenticated else None
    data['canClaim'] = bool(report.report_type == 'found' and report.moderation_status == 'approved' and not report.is_closed and report.expires_at > timezone.now() and report.site.is_active and report.category.is_active and request.user.pk != report.reporter_id and data['myClaim'] is None)
    if request.user.pk == report.reporter_id or can_manage(request.user, report):
        data['history'] = list(report.moderation_decisions.order_by('decided_at').values('decision', 'reason', 'decided_at'))
        data['closure'] = list(REPORT_CLOSURE.objects.filter(report=report).values('reason', 'closed_at'))[:1]
    if can_manage(request.user, report):
        data['custody'] = list(CUSTODY_RECEIPT.objects.filter(report=report).values('office_id', 'received_at', 'private_identifying_notes'))[:1]
        data['claims'] = [claim_data(c, request) for c in report.ownership_claims.select_related('report', 'claimant').order_by('-submitted_at')]
    return Response({'report': data})


@api_view(['GET'])
@permission_classes([AllowAny])
def report_image(request, pk):
    report = visible_report(request, pk)
    if not report.image or (report.photo_visibility_status != 'approved' and request.user.pk != report.reporter_id and not can_manage(request.user, report)):
        raise NotFound()
    try:
        response = FileResponse(report.image.open('rb'), content_type='image/jpeg')
    except (FileNotFoundError, OSError):
        raise NotFound('This photograph is no longer available.')
    response['Cache-Control'] = 'private, no-store'
    response['X-Content-Type-Options'] = 'nosniff'
    return response


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def close_report(request, pk):
    reason = serializers.CharField(allow_blank=True, max_length=2000).run_validation(request.data.get('reason', ''))
    if not reason or len(reason) > 255:
        raise ValidationError('Provide a closure reason of at most 255 characters.')
    with transaction.atomic():
        get_object_or_404(ITEM_REPORT.objects.select_for_update(), pk=pk)
        report = reports_query().get(pk=pk)
        manager = can_manage(request.user, report)
        if not manager and not (report.report_type == 'lost' and report.reporter_id == request.user.pk):
            raise PermissionDenied('Found item closure must be handled by authorized staff.')
        if report.is_closed or report.ownership_claims.filter(status='verified').exists():
            raise ValidationError('This report is already closed or has a verified claim awaiting release.')
        REPORT_CLOSURE.objects.create(report=report, closed_by=request.user, reason=reason)
        for claim in report.ownership_claims.filter(status='pending'):
            claim.status, claim.reviewer_remarks = 'rejected', 'The report has been closed by the campus office.'
            claim.reviewed_by, claim.reviewed_at = request.user, timezone.now()
            claim.save()
            notify(claim.claimant, report, f'Claim update for {report.reference_number}: the report was closed.')
        event(request.user, report, 'report_closed', reason)
        notify(report.reporter, report, f'{report.reference_number} was closed: {reason}')
    return Response({'report': report_data(reports_query().get(pk=pk), request)})


def claim_data(claim, request):
    return {'id': str(claim.pk), 'reportId': str(claim.report_id), 'reference': claim.report.reference_number,
        'title': claim.report.title, 'status': claim.status, 'explanation': claim.private_explanation,
        'remarks': claim.reviewer_remarks, 'submittedAt': claim.submitted_at, 'reviewedAt': claim.reviewed_at,
        'claimant': claim.claimant.get_full_name() or claim.claimant.username,
        'evidence': [{'id': str(e.pk), 'url': f'/claims/{claim.pk}/evidence/{e.pk}/', 'name': 'Ownership evidence', 'filename': 'ownership-evidence' + Path(e.file.name).suffix} for e in claim.evidence.all()],
        'released': RELEASE_RECORD.objects.filter(claim=claim).exists()}


def add_evidence(claim, uploads, saved_uploads):
    if len(uploads) > 3:
        raise ValidationError('Upload at most three evidence files per claim.')
    # Validate the complete batch before writing any file to private storage.
    for upload in uploads:
        if upload.size > 5 * 1024 * 1024:
            raise ValidationError('Each evidence file must be 5 MB or smaller.')
        content = upload.read(8)
        upload.seek(0)
        if content.startswith(b'%PDF-'):
            extension = '.pdf'
        elif content.startswith((bytes.fromhex('89504e47'), bytes.fromhex('ffd8ff'))):
            from PIL import Image
            try:
                with Image.open(upload) as image:
                    if image.format not in {'PNG', 'JPEG'} or image.width * image.height > 20_000_000:
                        raise ValueError('Unsupported evidence image')
                    image.verify()
                    extension = '.png' if image.format == 'PNG' else '.jpg'
            except (OSError, ValueError, Image.DecompressionBombError):
                raise ValidationError('Invalid evidence image; use PNG or JPEG with at most 20 megapixels.')
            upload.seek(0)
        else:
            raise ValidationError('Evidence must be a PDF, PNG, or JPEG file.')
        upload.name = uuid.uuid4().hex + extension
    for upload in uploads:
        evidence = CLAIM_EVIDENCE(claim=claim, file=upload)
        saved_uploads.append(evidence.file)
        evidence.save()


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def claims(request):
    if request.method == 'GET':
        records = OWNERSHIP_CLAIM.objects.filter(claimant=request.user).select_related('report', 'claimant').prefetch_related('evidence').order_by('-submitted_at')
        return page_response(records, request, lambda rows: [claim_data(row, request) for row in rows])
    report_id = serializers.UUIDField().run_validation(request.data.get('report'))
    serializer = ClaimWriteSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    with private_upload_scope() as saved_uploads, transaction.atomic():
        get_object_or_404(ITEM_REPORT.objects.select_for_update(), pk=report_id)
        report = get_object_or_404(public_reports(), pk=report_id)
        if report.report_type != 'found' or report.reporter_id == request.user.pk:
            raise ValidationError('You can claim an active found item reported by another person.')
        if report.ownership_claims.filter(claimant=request.user).exists():
            raise ValidationError('You already submitted a claim for this report. Follow its status in My Reports & Claims.')
        claim = serializer.save(report=report, claimant=request.user)
        add_evidence(claim, request.FILES.getlist('evidence'), saved_uploads)
        event(request.user, report, 'claim_submitted')
        notify(request.user, report, f'Your ownership claim for {report.reference_number} is pending verification.')
        notify_staff(report, f'Ownership claim awaiting verification: {report.reference_number}.')
    return Response({'claim': claim_data(claim, request)}, status=201)


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def withdraw_claim(request, pk):
    with transaction.atomic():
        initial = get_object_or_404(OWNERSHIP_CLAIM, pk=pk, claimant=request.user)
        get_object_or_404(ITEM_REPORT.objects.select_for_update(), pk=initial.report_id)
        claim = OWNERSHIP_CLAIM.objects.select_for_update().get(pk=pk)
        if claim.status != 'pending':
            raise ValidationError('Only pending claims can be withdrawn.')
        claim.status = 'withdrawn'
        claim.save(update_fields=['status'])
        event(request.user, claim.report, 'claim_withdrawn')
    return Response({'claim': claim_data(claim, request)})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def evidence_file(request, pk, evidence_id):
    evidence = get_object_or_404(CLAIM_EVIDENCE.objects.select_related('claim__report'), pk=evidence_id, claim_id=pk)
    if evidence.claim.claimant_id != request.user.pk and not can_manage(request.user, evidence.claim.report):
        raise NotFound()
    try:
        response = FileResponse(evidence.file.open('rb'), as_attachment=True, filename='ownership-evidence' + evidence.file.name[evidence.file.name.rfind('.'):])
    except (FileNotFoundError, OSError):
        raise NotFound('This evidence file is no longer available.')
    response['Cache-Control'] = 'private, no-store'
    response['X-Content-Type-Options'] = 'nosniff'
    return response


@api_view(['GET'])
@permission_classes([IsCampusStaff])
def staff_reports(request):
    records = filters(managed_reports(request.user), request.query_params)
    status = request.query_params.get('review')
    if status in {'pending', 'approved', 'rejected'}:
        records = records.filter(moderation_status=status, is_closed=False)
    elif status == 'closed':
        records = records.filter(is_closed=True)
    return page_response(records, request, lambda rows: ReportSerializer(rows, many=True, context={'request': request}).data)


@api_view(['POST'])
@permission_classes([IsCampusStaff])
def moderation(request, pk):
    decision = serializers.ChoiceField(choices=['approved', 'rejected', 'pending']).run_validation(request.data.get('decision'))
    reason = serializers.CharField(allow_blank=True, max_length=2000).run_validation(request.data.get('reason', ''))
    if decision not in {'approved', 'rejected', 'pending'} or len(reason) > 2000:
        raise ValidationError('Choose a valid moderation decision and reason.')
    if decision == 'rejected' and not reason:
        raise ValidationError('Explain why the report was rejected.')
    with transaction.atomic():
        get_object_or_404(ITEM_REPORT.objects.select_for_update(), pk=pk)
        report = reports_query().get(pk=pk)
        require_manager(request.user, report)
        if report.is_closed or report.ownership_claims.filter(status='verified').exists():
            raise ValidationError('A closed report or verified ownership claim prevents moderation changes.')
        MODERATION_DECISION.objects.create(report=report, reviewer=request.user, decision=decision, reason=reason)
        if report.image:
            report.photo_visibility_status = 'approved' if request.data.get('publish_photo') is True and decision == 'approved' else 'hidden'
            report.photo_reviewed_by, report.photo_reviewed_at = request.user, timezone.now()
            report.save(update_fields=['photo_visibility_status', 'photo_reviewed_by', 'photo_reviewed_at'])
        event(request.user, report, 'report_' + decision)
        notify(report.reporter, report, f'{report.reference_number}: {decision}. {reason}')
    return Response({'report': report_data(reports_query().get(pk=pk), request)})


@api_view(['POST'])
@permission_classes([IsCampusStaff])
def receive_item(request, pk):
    with transaction.atomic():
        get_object_or_404(ITEM_REPORT.objects.select_for_update(), pk=pk)
        report = reports_query().get(pk=pk)
        require_manager(request.user, report)
        office_id = serializers.IntegerField().run_validation(request.data.get('office'))
        office = get_object_or_404(OFFICE, pk=office_id, site_id=report.site_id, is_active=True)
        if report.report_type != 'found' or report.is_closed or report.has_custody:
            raise ValidationError('Only an open found report without a receipt can be received.')
        notes = serializers.CharField(allow_blank=True, max_length=4000).run_validation(request.data.get('notes', ''))
        if len(notes) > 4000:
            raise ValidationError('Keep identifying notes within 4000 characters.')
        CUSTODY_RECEIPT.objects.create(report=report, office=office, received_by=request.user, private_identifying_notes=notes)
        event(request.user, report, 'item_received')
        notify(report.reporter, report, f'{report.reference_number}: physical receipt recorded at {office.name}.')
    return Response({'message': 'Custody receipt recorded.'}, status=201)


@api_view(['POST'])
@permission_classes([IsCampusStaff])
def review_claim(request, pk):
    initial = get_object_or_404(OWNERSHIP_CLAIM, pk=pk)
    status = serializers.ChoiceField(choices=['verified', 'rejected']).run_validation(request.data.get('status'))
    remarks = serializers.CharField(max_length=2000).run_validation(request.data.get('remarks', ''))
    if status not in {'verified', 'rejected'} or not remarks or len(remarks) > 2000:
        raise ValidationError('Choose verified or rejected and provide verification remarks.')
    with transaction.atomic():
        get_object_or_404(ITEM_REPORT.objects.select_for_update(), pk=initial.report_id)
        report = reports_query().get(pk=initial.report_id)
        require_manager(request.user, report)
        claim = OWNERSHIP_CLAIM.objects.select_for_update().get(pk=pk)
        if claim.claimant_id == request.user.pk:
            raise PermissionDenied('Another authorized staff member must verify or release your own claim.')
        if claim.status not in {'pending', 'verified'} or RELEASE_RECORD.objects.filter(claim=claim).exists() or report.is_closed:
            raise ValidationError('This claim can no longer be reviewed.')
        if status == 'verified' and (not report.has_custody or report.moderation_status != 'approved' or report.ownership_claims.exclude(pk=pk).filter(status='verified').exists()):
            raise ValidationError('Verification requires approved listing, recorded custody, and no other verified owner.')
        claim.status, claim.reviewer_remarks, claim.reviewed_by, claim.reviewed_at = status, remarks, request.user, timezone.now()
        claim.save()
        event(request.user, report, 'claim_' + status)
        notify(claim.claimant, report, f'Claim for {report.reference_number}: {status}. {remarks}')
    return Response({'claim': claim_data(claim, request)})


@api_view(['POST'])
@permission_classes([IsCampusStaff])
def release_item(request, pk):
    initial = get_object_or_404(OWNERSHIP_CLAIM, pk=pk)
    location = serializers.CharField(max_length=255).run_validation(request.data.get('location', ''))
    if not location or len(location) > 255:
        raise ValidationError('Enter the actual handover location, within 255 characters.')
    with transaction.atomic():
        get_object_or_404(ITEM_REPORT.objects.select_for_update(), pk=initial.report_id)
        report = reports_query().get(pk=initial.report_id)
        require_manager(request.user, report)
        claim = OWNERSHIP_CLAIM.objects.select_for_update().get(pk=pk)
        if claim.claimant_id == request.user.pk:
            raise PermissionDenied('Another authorized staff member must verify or release your own claim.')
        if claim.status != 'verified' or report.report_type != 'found' or report.moderation_status != 'approved' or not report.has_custody or report.is_closed or report.is_released:
            raise ValidationError('Physical release requires verified ownership, custody, and an approved open found report.')
        RELEASE_RECORD.objects.create(claim=claim, released_by=request.user, handover_location=location)
        REPORT_CLOSURE.objects.create(report=report, closed_by=request.user, reason='Returned to verified owner')
        for other in report.ownership_claims.filter(status='pending'):
            other.status, other.reviewer_remarks = 'rejected', 'Item returned to a verified owner.'
            other.reviewed_by, other.reviewed_at = request.user, timezone.now()
            other.save()
            notify(other.claimant, report, f'{report.reference_number}: item returned to a verified owner.')
        event(request.user, report, 'item_released', location)
        notify(claim.claimant, report, f'{report.reference_number}: physical handover recorded at {location}.')
        notify(report.reporter, report, f'{report.reference_number}: item returned and report closed.')
    return Response({'message': 'Physical release and closure recorded.'}, status=201)


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def notifications(request):
    records = visible_notifications(request.user)
    if request.method == 'POST':
        records.filter(read_at__isnull=True).update(read_at=timezone.now())
    rows = list(records[:50].values('id', 'report_id', 'message', 'created_at', 'read_at', 'audience'))
    for row in rows:
        report_id = row['report_id']
        row['actionUrl'] = (f'/staff?report={report_id}' if row['audience'] == NOTIFICATION.Audience.OPERATIONS else f'/browse/{report_id}') if report_id else None
    return Response({'results': rows, 'unread': records.filter(read_at__isnull=True).count()})


@api_view(['GET'])
@permission_classes([IsCampusStaff])
def staff_summary(request):
    records = managed_reports(request.user)
    ids = records.values('pk')
    audits = AUDIT_EVENT.objects.select_related('actor').all()
    if not request.user.is_superuser:
        audits = audits.filter(site_id__in=staff_sites(request.user))
    stats = records.aggregate(total=Count('pk'), pending=Count('pk', filter=Q(moderation_status='pending', is_closed=False)), approved=Count('pk', filter=Q(moderation_status='approved', is_closed=False)), inCustody=Count('pk', filter=Q(has_custody=True, is_closed=False)), closed=Count('pk', filter=Q(is_closed=True)))
    stats['claims'] = OWNERSHIP_CLAIM.objects.filter(report_id__in=ids, status='pending').count()
    return Response({'stats': stats,
        'audit': [{'id': row.pk, 'actor': row.actor.username if row.actor else 'System', 'action': row.action, 'reference': row.reference, 'detail': row.detail, 'createdAt': row.created_at} for row in audits[:100]]})


@api_view(['GET'])
@permission_classes([IsCampusStaff])
def export_reports(request):
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Reference', 'Type', 'Title', 'Campus', 'Category', 'Review', 'Closed', 'In custody', 'Released', 'Incident date', 'Submitted at'])
    def safe(value):
        text = str(value)
        return "'" + text if text.startswith(('=', '+', '-', '@', '\t', '\r', '\n')) else text
    records = filters(managed_reports(request.user), request.query_params)
    review = request.query_params.get('review')
    if review in {'pending', 'approved', 'rejected'}:
        records = records.filter(moderation_status=review, is_closed=False)
    elif review == 'closed':
        records = records.filter(is_closed=True)
    for report in records.iterator():
        writer.writerow([safe(v) for v in [report.reference_number, report.report_type, report.title, report.site.name, report.category.name, report.moderation_status, report.is_closed, report.has_custody, report.is_released, report.item_date, report.created_at.isoformat()]])
    response = HttpResponse(output.getvalue(), content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="tipped-reports.csv"'
    response['Cache-Control'] = 'private, no-store'
    return response


@api_view(['GET', 'PATCH'])
@permission_classes([IsAuthenticated])
def account(request):
    user = request.user
    if request.method == 'PATCH':
        name = serializers.CharField(max_length=150).run_validation(request.data.get('fullName', user.get_full_name()))
        if not name or len(name) > 150:
            raise ValidationError('Enter your full name within 150 characters.')
        identity = request.data.get('studentNumber')
        with transaction.atomic():
            get_user_model().objects.select_for_update().get(pk=user.pk)
            first, _, last = name.partition(' ')
            user.first_name, user.last_name = first, last
            user.save(update_fields=['first_name', 'last_name'])
            if identity is not None:
                number = str(identity).strip()
                if not number or len(number) > 50:
                    raise ValidationError('Enter a student number within 50 characters.')
                site_id = serializers.IntegerField().run_validation(request.data.get('site'))
                program_id = serializers.IntegerField().run_validation(request.data.get('program'))
                site = get_object_or_404(SITE, pk=site_id, is_active=True)
                program = get_object_or_404(PROGRAM, pk=program_id)
                if STUDENT_PROFILE.objects.exclude(user=user).filter(student_number=number).exists():
                    raise ValidationError('That student number is already associated with an account.')
                current = STUDENT_PROFILE.objects.filter(user=user).first()
                changed = not current or (current.full_name, current.student_number, current.site_id, current.program_id) != (name, number, site_id, program_id)
                STUDENT_PROFILE.objects.update_or_create(user=user, defaults={'full_name': name, 'student_number': number, 'site': site, 'program': program, 'approval_status': 'pending' if changed else current.approval_status})
            else:
                STUDENT_PROFILE.objects.filter(user=user).exclude(full_name=name).update(full_name=name, approval_status='pending')
    return Response({'user': user_data(user)})


@api_view(['GET', 'POST'])
@permission_classes([IsAccountAdministrator])
def configuration(request):
    models = {'sites': SITE, 'categories': CATEGORY, 'programs': PROGRAM, 'offices': OFFICE}
    if request.method == 'POST':
        kind = serializers.ChoiceField(choices=list(models)).run_validation(request.data.get('kind'))
        if kind == 'sites' and not request.user.is_superuser:
            raise PermissionDenied('Only the Super Admin can change campus records.')
        model = models[kind]
        name = serializers.CharField(max_length=150).run_validation(request.data.get('name', ''))
        max_length = model._meta.get_field('name').max_length
        if not name or len(name) > max_length:
            raise ValidationError(f'Enter a name within {max_length} characters.')
        record_id = request.data.get('id')
        record = get_object_or_404(model, pk=serializers.IntegerField().run_validation(record_id)) if record_id else model()
        record.name = name
        if kind in {'sites', 'programs'}:
            code = serializers.CharField(max_length=32).run_validation(request.data.get('code', ''))
            if not code or len(code) > 32:
                raise ValidationError('Enter a code within 32 characters.')
            record.code = code
        if kind == 'offices':
            site_id = serializers.IntegerField().run_validation(request.data.get('site'))
            if record.pk and record.site_id != site_id:
                raise ValidationError('An existing office cannot be moved to another campus. Create a new office instead.')
            record.site = get_object_or_404(SITE, pk=site_id)
        if hasattr(record, 'is_active'):
            record.is_active = serializers.BooleanField().run_validation(request.data.get('is_active', True))
        record.full_clean()
        with transaction.atomic():
            record.save()
            AUDIT_EVENT.objects.create(actor=request.user, action='configuration_updated', detail=f'{kind} ID {record.pk}: {record.name}')
    return Response({kind: list(model.objects.order_by('name').values()) for kind, model in models.items()})


@api_view(['GET', 'PATCH'])
@permission_classes([IsAccountAdministrator])
def staff_users(request):
    User = get_user_model()
    owner = request.user.is_superuser
    if request.method == 'PATCH':
        allowed = {'id', 'isActive', 'approval'}
        if owner:
            allowed |= {'isAdmin', 'isOsa', 'siteIds'}
        if set(request.data) - allowed:
            raise PermissionDenied('Only the Super Admin can change roles or campus assignments; unsupported account fields are not editable here.')
        target_id = serializers.IntegerField().run_validation(request.data.get('id'))
        with transaction.atomic():
            user = get_object_or_404(User.objects.select_for_update(), pk=target_id)
            if user.pk == request.user.pk or user.is_superuser:
                raise PermissionDenied('Your own account and Super Admin accounts are protected. Superuser maintenance uses Django admin.')
            if not owner and is_privileged_account(user):
                raise PermissionDenied('Administrators can manage ordinary accounts only.')
            active = serializers.BooleanField().run_validation(request.data['isActive']) if 'isActive' in request.data else user.is_active
            approval = request.data.get('approval')
            if approval is not None:
                approval = serializers.ChoiceField(choices=['pending', 'approved', 'rejected']).run_validation(approval)
            profile = STUDENT_PROFILE.objects.select_for_update().filter(user=user).first()
            if approval is not None and profile is None:
                raise ValidationError('This account has no submitted student profile to review.')
            before = {'active': user.is_active, 'roles': list(user.groups.filter(name__in=[ADMIN_GROUP, OSA_GROUP]).values_list('name', flat=True)), 'approval': profile.approval_status if profile else None}
            admin_role = user.groups.filter(name=ADMIN_GROUP).exists()
            osa_role = user.groups.filter(name=OSA_GROUP).exists()
            if owner:
                if 'isAdmin' in request.data:
                    admin_role = serializers.BooleanField().run_validation(request.data['isAdmin'])
                if 'isOsa' in request.data:
                    osa_role = serializers.BooleanField().run_validation(request.data['isOsa'])
                if 'siteIds' in request.data:
                    ids = set(serializers.ListField(child=serializers.IntegerField(min_value=1), max_length=100).run_validation(request.data['siteIds']))
                    if ids and not osa_role:
                        raise ValidationError('Campus assignments require the OSA role.')
                    if SITE.objects.filter(pk__in=ids, is_active=True).count() != len(ids):
                        raise ValidationError('Choose existing active campuses.')
                elif not osa_role:
                    ids = set()
                else:
                    ids = set(user.staff_site_assignments.filter(is_active=True).values_list('site_id', flat=True))
                if 'isAdmin' in request.data or 'isOsa' in request.data:
                    for name, enabled in [(ADMIN_GROUP, admin_role), (OSA_GROUP, osa_role)]:
                        group, _ = Group.objects.get_or_create(name=name)
                        if enabled:
                            user.groups.add(group)
                        else:
                            user.groups.remove(group)
                    # Application operators do not need Django's admin-site flag.
                    user.is_staff = False
                previous_ids = set(user.staff_site_assignments.filter(is_active=True).values_list('site_id', flat=True))
                for site_id in previous_ids - ids:
                    user.staff_site_assignments.filter(site_id=site_id).update(is_active=False)
                for site_id in ids:
                    STAFF_SITE_ASSIGNMENT.objects.update_or_create(user=user, site_id=site_id, defaults={'is_active': True, 'permission_role': 'reviewer'})
                for site_id in sorted(previous_ids ^ ids):
                    AUDIT_EVENT.objects.create(actor=request.user, action='osa_campus_assignment_changed', detail=json.dumps({'target': user.pk, 'site': site_id, 'active': site_id in ids}))
            user.is_active = active
            user.save(update_fields=['is_active', 'is_staff'])
            if approval is not None:
                profile.approval_status = approval
                profile.save(update_fields=['approval_status'])
            after = {'active': user.is_active, 'roles': list(user.groups.filter(name__in=[ADMIN_GROUP, OSA_GROUP]).values_list('name', flat=True)), 'approval': profile.approval_status if profile else None}
            AUDIT_EVENT.objects.create(actor=request.user, action='account_permissions_updated', detail=json.dumps({'target': user.pk, 'before': before, 'after': after}, separators=(',', ':')))
    records = User.objects.select_related('student_profile__site', 'student_profile__program').prefetch_related(
        'groups', 'user_permissions', 'staff_site_assignments').order_by('username')
    if not owner:
        records = ordinary_accounts(records).exclude(pk=request.user.pk)
    q = request.query_params.get('q', '').strip()
    if q:
        records = records.filter(Q(username__icontains=q) | Q(email__icontains=q))
    def serialize(rows):
        return [{**user_data(user), 'isActive': user.is_active,
                 'isProtected': is_privileged_account(user),
                 'siteIds': [assignment.site_id for assignment in user.staff_site_assignments.all() if assignment.is_active]} for user in rows]
    return page_response(records, request, serialize)


@api_view(['GET'])
@permission_classes([AllowAny])
def api_root(request):
    paths = {'reports': '/api/reports/', 'campus_catalogue': '/api/catalogue/', 'my_profile': '/api/auth/profile/',
        'my_claims': '/api/claims/', 'notifications': '/api/notifications/', 'osa_reports': '/api/staff/reports/',
        'osa_summary': '/api/staff/summary/', 'django_admin': '/admin/'}
    return Response({'name': 'TIPPED Campus Lost & Found API', 'links': {name: request.build_absolute_uri(path) for name, path in paths.items()},
        'authentication': 'Login at POST /api/auth/login/; send Authorization: Bearer <access> for protected endpoints.',
        'report_details': 'Open the reports list and use an actual report UUID from its results. Pending reports appear only to their owner or authorized staff.'})
