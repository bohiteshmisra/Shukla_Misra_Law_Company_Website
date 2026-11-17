"""Security helpers: HTML sanitising, upload validation, CAPTCHA, text utilities."""
import random
import re
import unicodedata
import uuid
from pathlib import Path

import nh3
from flask import current_app, session

# ---------------------------------------------------------------- rich text
ALLOWED_TAGS = {
    "p", "br", "strong", "b", "em", "i", "u", "s", "h2", "h3", "h4", "ul", "ol", "li",
    "a", "blockquote", "table", "thead", "tbody", "tr", "th", "td", "hr",
}
ALLOWED_ATTRS = {"a": {"href", "title"}, "th": {"colspan", "rowspan"}, "td": {"colspan", "rowspan"}}


def sanitize_html(html):
    """Strip anything that is not plain formatting from admin-entered rich text."""
    return nh3.clean(
        html or "",
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRS,
        url_schemes={"http", "https", "mailto", "tel"},
        link_rel="noopener noreferrer",
    ).strip()


# ---------------------------------------------------------------- uploads
class UploadError(ValueError):
    pass


_ZIP = b"PK\x03\x04"
_OLE = b"\xd0\xcf\x11\xe0"
SIGNATURES = {
    "png": (b"\x89PNG\r\n\x1a\n",),
    "jpg": (b"\xff\xd8\xff",),
    "jpeg": (b"\xff\xd8\xff",),
    "webp": (b"RIFF",),
    "pdf": (b"%PDF-",),
    "docx": (_ZIP,),
    "xlsx": (_ZIP,),
    "doc": (_OLE,),
    "xls": (_OLE,),
}
UPLOAD_KINDS = {
    # kind: (allowed extensions, max bytes)
    "images": ({"png", "jpg", "jpeg", "webp"}, 3 * 1024 * 1024),
    "documents": ({"pdf", "docx", "xlsx", "doc", "xls"}, 10 * 1024 * 1024),
    "resumes": ({"pdf"}, 2 * 1024 * 1024),
}
PUBLIC_KINDS = {"images", "documents"}  # resumes are only served to the admin


def upload_dir(kind):
    path = Path(current_app.config["UPLOAD_DIR"]) / kind
    path.mkdir(parents=True, exist_ok=True)
    return path


def save_upload(file_storage, kind):
    """Validate extension, size and file signature; store under a random name."""
    allowed, max_bytes = UPLOAD_KINDS[kind]
    original = file_storage.filename or ""
    ext = original.rsplit(".", 1)[-1].lower() if "." in original else ""
    if ext not in allowed:
        raise UploadError("File type not allowed. Allowed: " + ", ".join(sorted(allowed)).upper() + ".")
    data = file_storage.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise UploadError(f"File is too large (limit {max_bytes // (1024 * 1024)} MB).")
    if not data.startswith(SIGNATURES[ext]) or (ext == "webp" and data[8:12] != b"WEBP"):
        raise UploadError("The file content does not match its type.")
    name = f"{uuid.uuid4().hex}.{ext}"
    (upload_dir(kind) / name).write_bytes(data)
    return name


def delete_upload(kind, name):
    if name and re.fullmatch(r"[0-9a-f]{32}\.[a-z]{3,4}", name):
        try:
            (upload_dir(kind) / name).unlink()
        except OSError:
            pass


# ---------------------------------------------------------------- captcha
def new_captcha(key):
    """Create an arithmetic challenge, remember the answer in the session."""
    a, b = random.randint(2, 9), random.randint(1, 9)
    session[f"captcha_{key}"] = str(a + b)
    return f"{a} + {b}"


def check_captcha(key, answer):
    expected = session.pop(f"captcha_{key}", None)
    return expected is not None and (answer or "").strip() == expected


# ---------------------------------------------------------------- text
def slugify(text):
    text = unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:100] or "item"


def csv_safe(value):
    """Neutralise spreadsheet formula injection in exported cells."""
    text = "" if value is None else str(value)
    return "'" + text if text[:1] in ("=", "+", "-", "@", "\t", "\r") else text
