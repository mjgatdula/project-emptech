from django.core.management.base import BaseCommand
from django.db import transaction
from base.models import SITE, CATEGORY, OFFICE


class Command(BaseCommand):
    help = 'Create the campus/category configuration used by TIPPED. No accounts or reports are created.'

    @transaction.atomic
    def handle(self, *args, **options):
        for code, name in [('ARL', 'Arlegui'), ('CAS', 'Casal')]:
            site = SITE.objects.filter(name__iexact=name).first()
            if site is None:
                site, _ = SITE.objects.get_or_create(code=code, defaults={'name': name})
            OFFICE.objects.get_or_create(site=site, name='Office of Student Affairs')
        for name in ['Electronics', 'ID / Cards', 'Personal belongings', 'School supplies', 'Other']:
            CATEGORY.objects.get_or_create(name=name)
        self.stdout.write(self.style.SUCCESS('Campus, category and receiving-office configuration is ready. No demo accounts or reports were added.'))
