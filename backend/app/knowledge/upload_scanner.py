from __future__ import annotations

import json
from hashlib import sha256
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener

from app.core.config import Settings


class UploadScanError(Exception):
    """Raised when a required scanner cannot establish that an upload is clean."""


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001
        return None


def require_clean_upload(*, content: bytes, media_type: str, settings: Settings) -> None:
    """Run a configured trusted scanner before bytes reach private object storage.

    The scanner address is operator configuration, never request input. Any
    unavailable, redirected, malformed, or non-clean response rejects the upload.
    """
    if not settings.knowledge_upload_scanning_required:
        return

    request = Request(
        settings.knowledge_upload_scanner_url,
        data=content,
        method="POST",
        headers={
            "Content-Type": media_type,
            "X-Content-SHA256": sha256(content).hexdigest(),
        },
    )
    try:
        with build_opener(_NoRedirect()).open(
            request,
            timeout=settings.knowledge_upload_scanner_timeout_seconds,
        ) as response:
            if response.status != 200:
                raise UploadScanError("scanner did not return success")
            raw_response = response.read(8_192)
    except (HTTPError, URLError, OSError, TimeoutError) as exc:
        raise UploadScanError("scanner unavailable") from exc

    try:
        result = json.loads(raw_response.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise UploadScanError("scanner returned an invalid response") from exc
    if not isinstance(result, dict) or result.get("status") != "clean":
        raise UploadScanError("scanner did not mark upload clean")
