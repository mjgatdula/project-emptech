from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand
from base.permissions import ADMIN_GROUP, OSA_GROUP


class Command(BaseCommand):
    help = 'Create TIPPED role groups idempotently. Does not assign users or grant Django model permissions.'

    def handle(self, *args, **options):
        for name in [ADMIN_GROUP, OSA_GROUP]:
            _, created = Group.objects.get_or_create(name=name)
            self.stdout.write(f"{name}: {'created' if created else 'already exists'}")
        self.stdout.write('No user memberships or account privileges were changed.')
