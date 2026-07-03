import io

import pytest
from pypdf import PdfWriter

from app.core.document_validation import (
    FileTooLargeError,
    PasswordProtectedFileError,
    UnsupportedExtensionError,
    check_password_protected,
    validate_extension,
    validate_size,
    validate_upload,
)


def _make_plain_pdf_bytes() -> bytes:
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    buffer = io.BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def _make_encrypted_pdf_bytes() -> bytes:
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    writer.encrypt(user_password="secret", owner_password="owner-secret")
    buffer = io.BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def test_validate_extension_accepts_allowed_types():
    assert validate_extension("handbook.pdf") == "pdf"
    assert validate_extension("notes.md") == "md"


def test_validate_extension_rejects_disallowed_types():
    with pytest.raises(UnsupportedExtensionError):
        validate_extension("archive.zip")


def test_validate_size_rejects_oversized_file():
    with pytest.raises(FileTooLargeError):
        validate_size(600 * 1024 * 1024)


def test_validate_size_rejects_empty_file():
    with pytest.raises(Exception, match="empty"):
        validate_size(0)


def test_check_password_protected_detects_encrypted_pdf():
    assert check_password_protected("pdf", _make_encrypted_pdf_bytes()) is True
    assert check_password_protected("pdf", _make_plain_pdf_bytes()) is False


def test_check_password_protected_skips_non_pdf_formats():
    assert check_password_protected("txt", b"plain text content") is False


def test_validate_upload_rejects_password_protected_pdf():
    with pytest.raises(PasswordProtectedFileError):
        validate_upload(
            filename="secret.pdf", size_bytes=100, content=_make_encrypted_pdf_bytes()
        )


def test_validate_upload_accepts_valid_pdf():
    content = _make_plain_pdf_bytes()
    extension = validate_upload(filename="handbook.pdf", size_bytes=len(content), content=content)
    assert extension == "pdf"
