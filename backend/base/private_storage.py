"""Private S3-compatible storage: all downloads still pass Django authorization."""
from storages.backends.s3 import S3Storage


class PrivateObjectStorage(S3Storage):
    default_acl = None
    file_overwrite = False
    custom_domain = None

    def url(self, name, *args, **kwargs):
        raise ValueError('Private files require an authorized download endpoint.')
