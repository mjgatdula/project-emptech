"""Export referenced private objects with hashes; never publishes or deletes files."""
import hashlib
import json
import os
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from base.models import ITEM_REPORT, CLAIM_EVIDENCE


class Command(BaseCommand):
    help = 'Export referenced private photos/evidence to a NEW private backup directory.'

    def add_arguments(self, parser):
        parser.add_argument('--directory', required=True)

    def handle(self, *args, **options):
        root = Path(options['directory']).resolve()
        if root.exists():
            raise CommandError('Use a new backup directory; existing backups are never overwritten.')
        root.mkdir(parents=True, mode=0o700)
        manifest = []
        seen = set()
        for model, field in [(ITEM_REPORT, 'image'), (CLAIM_EVIDENCE, 'file')]:
            for row in model.objects.exclude(**{field: ''}).only(field).iterator():
                item = getattr(row, field)
                if not item.name or item.name in seen:
                    continue
                name = item.name
                destination = (root / name).resolve()
                if '\\' in name or not destination.is_relative_to(root) or destination == root:
                    raise CommandError('Unsafe stored object name; export stopped.')
                destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
                digest = hashlib.sha256()
                size = 0
                try:
                    with item.open('rb') as source, os.fdopen(os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), 'wb') as target:
                        for chunk in iter(lambda: source.read(1024 * 1024), b''):
                            target.write(chunk)
                            digest.update(chunk)
                            size += len(chunk)
                except Exception:
                    raise CommandError('Private object export failed; this is an INCOMPLETE backup.') from None
                manifest.append({'name': name, 'bytes': size, 'sha256': digest.hexdigest()})
                seen.add(name)
        with os.fdopen(os.open(root / 'manifest.json', os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), 'w', encoding='utf-8') as output:
            json.dump(manifest, output, indent=2)
        self.stdout.write(f'Exported {len(manifest)} private objects. Keep this backup private and encrypted at rest. Freeze writes for a database/file-consistent backup.')
