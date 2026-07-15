from storages.backends.s3boto3 import S3Boto3Storage


class R2MediaStorage(S3Boto3Storage):
    """
    Cloudflare R2 storage backend for user-uploaded media
    (gallery photos, volunteer photos, etc.)
    """
    default_acl = None          # R2 ACL ko support nahi karta
    file_overwrite = False      # same naam ki file overwrite na ho
    querystring_auth = False    # public URLs bina signed query params ke