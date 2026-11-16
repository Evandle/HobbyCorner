from django.conf import settings
from django.core.exceptions import ValidationError


def validate_university_email(value):
    """Enforce UNIVERSITY_EMAIL_DOMAINS (from .env). Empty or missing = any email.

    To require school emails later, set e.g. UNIVERSITY_EMAIL_DOMAINS=cit.edu.
    A domain also matches its subdomains (students.cit.edu), but never a
    look-alike such as notcit.edu or cit.edu.evil.com.
    """
    domains = getattr(settings, "UNIVERSITY_EMAIL_DOMAINS", [])
    if not domains:
        return
    host = value.rsplit("@", 1)[-1].lower()
    if not any(host == domain or host.endswith("." + domain) for domain in domains):
        allowed = ", ".join(f"@{domain}" for domain in domains)
        raise ValidationError(
            f"Please use your university email ({allowed}).",
            code="not_university_email",
        )
