"""Document upload validation (docs/05-task.md Phase 4 "Validation").

Extension + size are enforced strictly. MIME sniffing from the
client-declared `Content-Type` is inherently unreliable (any client can
send any value), so we validate by extension rather than rejecting on a
mismatched declared type — the extension is what determines which parser
a later phase will use anyway.

Password-protection detection is only implemented for PDF (via pypdf);
other formats don't have a cheap, reliable way to detect this and are
treated as not password-protected. Virus scanning is a documented no-op
hook — no antivirus engine is wired up yet; replacing `scan_for_viruses`
with a real ClamAV (or similar) call is the only change needed later.
"""

import hashlib
import io

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from app.core.config import get_settings
from app.core.exceptions import AppError


class DocumentValidationError(AppError):
    status_code = 400
    code = "VALIDATION_ERROR"


class FileTooLargeError(DocumentValidationError):
    code = "FILE_TOO_LARGE"


class UnsupportedExtensionError(DocumentValidationError):
    code = "UNSUPPORTED_EXTENSION"


class PasswordProtectedFileError(DocumentValidationError):
    code = "PASSWORD_PROTECTED_FILE"


def get_extension(filename: str) -> str:
    if "." not in filename:
        return ""
    return filename.rsplit(".", 1)[-1].lower()


def validate_extension(filename: str) -> str:
    settings = get_settings()
    extension = get_extension(filename)
    if extension not in settings.allowed_upload_extensions:
        allowed = ", ".join(settings.allowed_upload_extensions)
        raise UnsupportedExtensionError(
            f"'.{extension}' is not a supported file type. Allowed: {allowed}."
        )
    return extension


def validate_size(size_bytes: int) -> None:
    settings = get_settings()
    if size_bytes > settings.max_upload_size_bytes:
        max_mb = settings.max_upload_size_bytes // (1024 * 1024)
        raise FileTooLargeError(f"File exceeds the maximum allowed size of {max_mb} MB.")
    if size_bytes == 0:
        raise DocumentValidationError("File is empty.", code="EMPTY_FILE")


def check_password_protected(extension: str, content: bytes) -> bool:
    if extension != "pdf":
        return False
    try:
        reader = PdfReader(io.BytesIO(content))
        return reader.is_encrypted
    except PdfReadError:
        # Malformed PDFs are caught by the parser in a later phase, not here.
        return False


def scan_for_viruses(content: bytes) -> bool:
    """Returns True if the file is clean. Always True today — no antivirus
    engine is integrated yet. Kept as an explicit call site so wiring in a
    real scanner (e.g. ClamAV) later is a one-function change."""
    return True


def compute_sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def validate_upload(*, filename: str, size_bytes: int, content: bytes) -> str:
    """Runs the full validation pipeline and returns the validated
    extension. Raises a `DocumentValidationError` subclass on failure."""
    extension = validate_extension(filename)
    validate_size(size_bytes)

    if check_password_protected(extension, content):
        raise PasswordProtectedFileError(
            "This file is password-protected. Remove the password and re-upload."
        )

    if not scan_for_viruses(content):
        raise DocumentValidationError("This file failed a virus scan.", code="VIRUS_DETECTED")

    return extension
