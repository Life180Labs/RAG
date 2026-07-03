"""Parser factory — dispatches by file extension to the matching module,
per the format table in docs/02-architecture.md section 25."""

from collections.abc import Callable

from document_worker.parsing import (
    csv_parser,
    docx_parser,
    html_parser,
    json_parser,
    markdown_parser,
    pdf_parser,
    txt_parser,
    xml_parser,
)

ParseFn = Callable[[bytes], tuple[list[dict], int | None]]

_PARSERS: dict[str, tuple[ParseFn, str]] = {
    "pdf": (pdf_parser.parse, "pymupdf"),
    "docx": (docx_parser.parse, "python-docx"),
    "html": (html_parser.parse, "beautifulsoup4"),
    "md": (markdown_parser.parse, "markdown-it-py"),
    "txt": (txt_parser.parse, "native"),
    "csv": (csv_parser.parse, "pandas"),
    "json": (json_parser.parse, "native"),
    "xml": (xml_parser.parse, "lxml"),
}


class UnsupportedExtensionError(ValueError):
    pass


def get_parser(extension: str) -> tuple[ParseFn, str]:
    entry = _PARSERS.get(extension.lower())
    if entry is None:
        raise UnsupportedExtensionError(f"No parser registered for '.{extension}'.")
    return entry
