"""Rules for pictures people upload (profile photos, chat pictures).

One copy, so the security-relevant check can't drift between features.
"""
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import UploadedFile

MAX_PICTURE_BYTES = 2 * 1024 * 1024
PICTURE_FORMATS = {"JPEG", "PNG", "GIF", "WEBP"}
ACCEPT_PICTURES = "image/jpeg,image/png,image/gif,image/webp"  # hint for the file picker only


def check_picture(upload):
    """Return `upload` if it is fine; raise ValidationError if not.

    Only a freshly uploaded file is checked. A stored file or a cleared value
    (False/None) passes straight through.
    """
    if not isinstance(upload, UploadedFile):
        return upload
    if upload.size > MAX_PICTURE_BYTES:
        raise ValidationError("Please choose a picture under 2 MB.")
    # Django's ImageField has already opened the file with Pillow, so this is
    # the file's real format, not its name or what the browser claimed.
    if upload.image.format not in PICTURE_FORMATS:
        raise ValidationError("Please upload a JPEG, PNG, GIF or WEBP picture.")
    return upload
