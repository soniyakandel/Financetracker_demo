from urllib.parse import urljoin, urlparse

from flask import request


def is_safe_url(target):
    if not target:
        return False
    host_url = urlparse(request.host_url)
    candidate = urlparse(urljoin(request.host_url, target))
    return candidate.scheme in ("http", "https") and host_url.netloc == candidate.netloc


def safe_redirect_target(candidate, fallback):
    return candidate if is_safe_url(candidate) else fallback
