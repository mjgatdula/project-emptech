"""One-time, explicitly scoped cleanup with a Windows-user encrypted recovery archive."""
import ctypes
from ctypes import wintypes
import io
import json
import os
from pathlib import Path
import zipfile
from django.contrib.auth import get_user_model
from django.core import serializers
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from base.models import (ITEM_REPORT, OWNERSHIP_CLAIM, CLAIM_EVIDENCE, CUSTODY_RECEIPT,
    MODERATION_DECISION, RELEASE_RECORD, REPORT_CLOSURE, NOTIFICATION, AUDIT_EVENT, STUDENT_PROFILE, STAFF_SITE_ASSIGNMENT)

APPROVED_TEST_EMAILS = frozenset({'ja@gmail.com','ja2@gmail.com'})


def protect(data):
    if os.name!='nt': raise CommandError('This cleanup archive uses Windows DPAPI; run it as the local project owner on Windows.')
    class Blob(ctypes.Structure):
        _fields_=[('size',wintypes.DWORD),('data',ctypes.POINTER(ctypes.c_ubyte))]
    source=ctypes.create_string_buffer(data)
    original=Blob(len(data),ctypes.cast(source,ctypes.POINTER(ctypes.c_ubyte)))
    encrypted=Blob()
    fn=ctypes.windll.crypt32.CryptProtectData
    fn.argtypes=[ctypes.POINTER(Blob),wintypes.LPCWSTR,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p,wintypes.DWORD,ctypes.POINTER(Blob)]
    fn.restype=wintypes.BOOL
    if not fn(ctypes.byref(original),'TIPPED scoped test cleanup',None,None,None,1,ctypes.byref(encrypted)):
        raise CommandError('Could not encrypt the recovery archive. Nothing deleted.')
    try: return ctypes.string_at(encrypted.data,encrypted.size)
    finally:
        ctypes.windll.kernel32.LocalFree.argtypes=[ctypes.c_void_p]
        ctypes.windll.kernel32.LocalFree(ctypes.cast(encrypted.data,ctypes.c_void_p))


class Command(BaseCommand):
    help = 'Dry-run by default. Only owner-approved ja@gmail.com and ja2@gmail.com can be selected.'

    def add_arguments(self, parser):
        parser.add_argument('--email',action='append',required=True)
        parser.add_argument('--apply',action='store_true')
        parser.add_argument('--backup-dir',default=str(Path.home()/'.codex'/'backups'/'tipped'))

    def handle(self,*args,**options):
        emails={value.casefold().strip() for value in options['email']}
        if not emails or not emails<=APPROVED_TEST_EMAILS: raise CommandError('Only explicitly approved test emails are allowed.')
        User=get_user_model()
        query=Q(pk__in=[])
        for email in emails: query |= Q(email__iexact=email)
        with transaction.atomic():
            users=list(User.objects.select_for_update().filter(query))
            ids=[u.pk for u in users]
            if any(u.is_superuser for u in users): raise CommandError('Super Admin accounts are protected. Nothing deleted.')
            reports=list(ITEM_REPORT.objects.select_for_update().filter(reporter_id__in=ids))
            report_ids=[r.pk for r in reports]
            claims=list(OWNERSHIP_CLAIM.objects.filter(Q(report_id__in=report_ids)|Q(claimant_id__in=ids)))
            if any(c.report_id not in report_ids for c in claims): raise CommandError('A selected account participates in a report outside this cleanup. Review it first.')
            for model,field in [(CUSTODY_RECEIPT,'received_by'),(MODERATION_DECISION,'reviewer'),(REPORT_CLOSURE,'closed_by')]:
                if model.objects.filter(**{field+'_id__in':ids}).exclude(report_id__in=report_ids).exists(): raise CommandError('Protected operational history exists outside the test reports.')
            claim_ids=[c.pk for c in claims]
            if RELEASE_RECORD.objects.filter(released_by_id__in=ids).exclude(claim_id__in=claim_ids).exists(): raise CommandError('Protected release history exists outside the test reports.')
            evidence=list(CLAIM_EVIDENCE.objects.filter(claim_id__in=claim_ids))
            batches=[users,reports,claims,evidence,
                list(CUSTODY_RECEIPT.objects.filter(report_id__in=report_ids)),list(MODERATION_DECISION.objects.filter(report_id__in=report_ids)),
                list(RELEASE_RECORD.objects.filter(claim_id__in=claim_ids)),list(REPORT_CLOSURE.objects.filter(report_id__in=report_ids)),
                list(NOTIFICATION.objects.filter(Q(report_id__in=report_ids)|Q(user_id__in=ids))),
                list(AUDIT_EVENT.objects.filter(Q(report_id__in=report_ids)|Q(actor_id__in=ids))),
                list(STUDENT_PROFILE.objects.filter(user_id__in=ids)),list(STAFF_SITE_ASSIGNMENT.objects.filter(user_id__in=ids))]
            files=[r.image for r in reports if r.image]+[e.file for e in evidence if e.file]
            self.stdout.write(f'Scope: {len(users)} approved test accounts, {len(reports)} reports, {len(claims)} claims, {len(files)} private files.')
            if not options['apply']:
                self.stdout.write('DRY RUN: nothing deleted. Existing non-selected Super Admins, campus catalogue and other accounts remain.'); return
            if not users: self.stdout.write('No selected test accounts remain.'); return
            archive=io.BytesIO()
            with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as output:
                output.writestr('records.json',serializers.serialize('json',[row for batch in batches for row in batch]))
                manifest=[]
                for index,field in enumerate(files):
                    key=f'files/{index}'
                    try:
                        with field.storage.open(field.name,'rb') as source: output.writestr(key,source.read())
                    except FileNotFoundError: key=None
                    manifest.append({'archive':key,'original':field.name})
                output.writestr('file-manifest.json',json.dumps(manifest))
            backup_dir=Path(options['backup_dir']).resolve()
            backup_dir.mkdir(parents=True,exist_ok=True)
            backup=backup_dir/f'test-cleanup-{timezone.now():%Y%m%dT%H%M%S%f}.dpapi'
            with backup.open('xb') as target:
                target.write(protect(archive.getvalue())); target.flush(); os.fsync(target.fileno())
            RELEASE_RECORD.objects.filter(claim_id__in=claim_ids).delete()
            REPORT_CLOSURE.objects.filter(report_id__in=report_ids).delete()
            CUSTODY_RECEIPT.objects.filter(report_id__in=report_ids).delete()
            MODERATION_DECISION.objects.filter(report_id__in=report_ids).delete()
            OWNERSHIP_CLAIM.objects.filter(pk__in=claim_ids).delete()
            NOTIFICATION.objects.filter(Q(report_id__in=report_ids)|Q(user_id__in=ids)).delete()
            AUDIT_EVENT.objects.filter(report_id__in=report_ids).delete()
            ITEM_REPORT.objects.filter(pk__in=report_ids).delete()
            User.objects.filter(pk__in=ids).delete()
        failures=0
        for field in files:
            try: field.storage.delete(field.name)
            except OSError: failures+=1
        self.stdout.write(f'Cleanup committed. Encrypted recovery archive: {backup}')
        self.stdout.write(f'Private-file cleanup failures: {failures}. Non-selected accounts and catalogue preserved.')
