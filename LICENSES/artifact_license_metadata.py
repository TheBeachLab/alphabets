# SPDX-FileCopyrightText: 2014-2026 The Beach Lab <https://beachlab.org>
# SPDX-License-Identifier: MIT
"""Embed SPDX declarations in portable generated-artifact metadata."""

from __future__ import annotations

import argparse
import binascii
import html
import re
import struct
import tempfile
import zipfile
from pathlib import Path

from json_license_metadata import JSON_LICENSE_METADATA

# REUSE-IgnoreStart
DEFAULT_LICENSE_TEXT = (
    "SPDX-File"
    "CopyrightText: "
    + JSON_LICENSE_METADATA["SPDX-FileCopyrightText"]
    + "\nSPDX-License"
    + "-Identifier: "
    + JSON_LICENSE_METADATA["SPDX-License-Identifier"]
)
LICENSE_URL = "https://github.com/TheBeachLab/alphabets/blob/master/LICENSE"
SUPPORTED_SUFFIXES = {
    ".drl",
    ".dxf",
    ".gm1",
    ".gtl",
    ".gto",
    ".gts",
    ".jpeg",
    ".jpg",
    ".pdf",
    ".png",
    ".step",
    ".stl",
    ".svg",
    ".zip",
}
BEGIN = "ALPHABETS_LICENSE_BEGIN"
END = "ALPHABETS_LICENSE_END"


class ArtifactLicenseMetadataError(ValueError):
    """Raised when artifact metadata is missing, invalid, or unsafe to add."""


def artifact_suffix(path: Path) -> str:
    suffix = path.suffix.lower()
    return suffix or (
        path.name.lower() if path.name.lower() in SUPPORTED_SUFFIXES else ""
    )


def adjacent_license_text(path: Path) -> str:
    sidecar = Path(f"{path}.license")
    if sidecar.exists():
        return sidecar.read_text(encoding="utf-8").strip()
    existing = embedded_license_text(path)
    return existing.strip() if _valid_spdx_text(existing) else DEFAULT_LICENSE_TEXT


def _valid_spdx_text(text: str) -> bool:
    copyright_label = "SPDX-FileCopyrightText:"
    licence_label = "SPDX-License-Identifier:"
    return any(line.startswith(copyright_label) for line in text.splitlines()) and any(
        line.startswith(licence_label) and line.removeprefix(licence_label).strip()
        for line in text.splitlines()
    )


def _xml_metadata(license_text: str) -> str:
    return (
        '<metadata id="alphabets-license">\n'
        + html.escape(license_text, quote=False)
        + "\n</metadata>"
    )


def _embed_svg(path: Path, license_text: str) -> None:
    document = path.read_text(encoding="utf-8")
    document = re.sub(
        r'\s*(?:<!-- alphabets-license.*?-->\s*)?<metadata id="alphabets-license">.*?</metadata>',
        "",
        document,
        flags=re.DOTALL,
    )
    root = re.search(r"<svg\b[^>]*>", document, flags=re.DOTALL)
    if root is None:
        raise ArtifactLicenseMetadataError(f"{path}: no SVG root element")
    comment = "<!-- alphabets-license\n" + license_text + "\n-->"
    document = (
        document[: root.end()]
        + "\n  "
        + comment
        + "\n  "
        + _xml_metadata(license_text)
        + document[root.end() :]
    )
    path.write_text(document, encoding="utf-8")


def _png_chunks(document: bytes):
    if not document.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ArtifactLicenseMetadataError("invalid PNG signature")
    offset = 8
    while offset < len(document):
        length = struct.unpack_from(">I", document, offset)[0]
        chunk_end = offset + 12 + length
        if chunk_end > len(document):
            raise ArtifactLicenseMetadataError("truncated PNG chunk")
        yield document[offset:chunk_end]
        offset = chunk_end


def _png_chunk(kind: bytes, data: bytes) -> bytes:
    return (
        struct.pack(">I", len(data))
        + kind
        + data
        + struct.pack(">I", binascii.crc32(kind + data) & 0xFFFFFFFF)
    )


def _embed_png(path: Path, license_text: str) -> None:
    document = path.read_bytes()
    chunks = []
    for chunk in _png_chunks(document):
        length = struct.unpack_from(">I", chunk)[0]
        kind = chunk[4:8]
        data = chunk[8 : 8 + length]
        if kind == b"tEXt" and data.startswith(b"License\0"):
            continue
        chunks.append(chunk)
        if kind == b"IHDR":
            chunks.append(
                _png_chunk(b"tEXt", b"License\0" + license_text.encode("latin-1"))
            )
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + b"".join(chunks))


def _embed_jpeg(path: Path, license_text: str) -> None:
    document = path.read_bytes()
    if not document.startswith(b"\xff\xd8"):
        raise ArtifactLicenseMetadataError(f"{path}: invalid JPEG signature")
    if document[2:4] == b"\xff\xfe":
        length = struct.unpack_from(">H", document, 4)[0]
        payload = document[6 : 4 + length]
        if payload.startswith(b"SPDX-FileCopyrightText:"):
            document = document[:2] + document[4 + length :]
    payload = license_text.encode("utf-8")
    if len(payload) > 65533:
        raise ArtifactLicenseMetadataError("JPEG licence comment is too long")
    segment = b"\xff\xfe" + struct.pack(">H", len(payload) + 2) + payload
    path.write_bytes(document[:2] + segment + document[2:])


def _embed_pdf(path: Path, license_text: str) -> None:
    try:
        from pypdf import PdfReader, PdfWriter
    except ImportError as error:
        raise ArtifactLicenseMetadataError("PDF embedding requires pypdf") from error
    reader = PdfReader(path)
    writer = PdfWriter(clone_from=reader)
    metadata = {
        str(key): str(value)
        for key, value in (reader.metadata or {}).items()
        if value is not None
    }
    metadata.update(
        {
            "/Copyright": "Copyright (c) 2014-2026 The Beach Lab (https://beachlab.org)",
            "/License": "MIT",
            "/LicenseURL": LICENSE_URL,
            "/SPDX": license_text,
        }
    )
    writer.add_metadata(metadata)
    with tempfile.NamedTemporaryFile(
        dir=path.parent, suffix=".pdf", delete=False
    ) as temporary:
        temporary_path = Path(temporary.name)
        writer.write(temporary)
    temporary_path.replace(path)


def _pdf_info_value(document: bytes, key: bytes) -> str:
    marker = b"/" + key + b" "
    start = document.find(marker)
    if start < 0:
        return ""
    start += len(marker)
    if document[start : start + 1] == b"<":
        end = document.find(b">", start + 1)
        try:
            return bytes.fromhex(document[start + 1 : end].decode()).decode("utf-8")
        except (UnicodeDecodeError, ValueError):
            return ""
    if document[start : start + 1] != b"(":
        return ""
    value = bytearray()
    depth = 1
    index = start + 1
    while index < len(document) and depth:
        byte = document[index]
        if byte == 0x5C:
            octal = re.match(rb"[0-7]{1,3}", document[index + 1 : index + 4])
            if octal:
                value.append(int(octal.group(), 8))
                index += 1 + len(octal.group())
                continue
            index += 1
            if index < len(document):
                value.append(document[index])
        elif byte == 0x28:
            depth += 1
            value.append(byte)
        elif byte == 0x29:
            depth -= 1
            if depth:
                value.append(byte)
        else:
            value.append(byte)
        index += 1
    return value.decode("utf-8", errors="replace") if depth == 0 else ""


def _replace_text_block(document: str, prefix: str, license_text: str) -> str:
    begin = f"{prefix}{BEGIN}"
    end = f"{prefix}{END}"
    document = re.sub(
        rf"^{re.escape(begin)}\r?\n.*?^{re.escape(end)}\r?\n?",
        "",
        document,
        flags=re.MULTILINE | re.DOTALL,
    )
    block = "\n".join(
        [begin, *(f"{prefix}{line}" for line in license_text.splitlines()), end]
    )
    return block + "\n" + document


def _embed_step(path: Path, license_text: str) -> None:
    document = path.read_text(encoding="utf-8", errors="strict")
    prefix = "/* "
    begin = f"{prefix}{BEGIN} */"
    end = f"{prefix}{END} */"
    document = re.sub(
        rf"^{re.escape(begin)}\r?\n.*?^{re.escape(end)}\r?\n?",
        "",
        document,
        flags=re.MULTILINE | re.DOTALL,
    )
    block = "\n".join(
        [begin, *(f"/* {line} */" for line in license_text.splitlines()), end]
    )
    marker = "ISO-10303-21;"
    if marker not in document:
        raise ArtifactLicenseMetadataError(f"{path}: invalid STEP header")
    document = document.replace(marker, marker + "\n" + block, 1)
    path.write_text(document, encoding="utf-8")


def _embed_dxf(path: Path, license_text: str) -> None:
    document = path.read_text(encoding="utf-8", errors="strict")
    begin = f"999\n{BEGIN}\n"
    end = f"999\n{END}\n"
    document = re.sub(
        rf"^\s*999\r?\n{re.escape(BEGIN)}\r?\n.*?^\s*999\r?\n{re.escape(END)}\r?\n?",
        "",
        document,
        flags=re.MULTILINE | re.DOTALL,
    )
    block = (
        begin + "".join(f"999\n{line}\n" for line in license_text.splitlines()) + end
    )
    section = re.search(
        r"^\s*0\r?\nSECTION\r?\n\s*2\r?\nHEADER\r?\n",
        document,
        flags=re.MULTILINE,
    )
    if not section:
        section = re.search(
            r"^\s*0\r?\nSECTION\r?\n\s*2\r?\n[^\r\n]+\r?\n",
            document,
            flags=re.MULTILINE,
        )
    if not section:
        raise ArtifactLicenseMetadataError(f"{path}: invalid DXF section")
    document = document[: section.end()] + block + document[section.end() :]
    path.write_text(document, encoding="utf-8")


def _binary_stl(path: Path) -> bool:
    document = path.read_bytes()
    if len(document) < 84:
        return False
    triangles = struct.unpack_from("<I", document, 80)[0]
    return len(document) == 84 + 50 * triangles


def _embed_stl(path: Path, license_text: str) -> None:
    if not _binary_stl(path):
        raise ArtifactLicenseMetadataError(
            f"{path}: only binary STL has safe native metadata"
        )
    licence_match = re.search(r"SPDX-License" r"-Identifier:\s*([^\n]+)", license_text)
    licence = licence_match.group(1).strip() if licence_match else "MIT"
    header = (
        f"SPDX-License{'-Identifier'}: {licence}; Copyright 2014-2026 The Beach Lab"
    ).encode()
    if len(header) > 80:
        raise ArtifactLicenseMetadataError(
            f"{path}: STL metadata exceeds its 80-byte header"
        )
    document = path.read_bytes()
    path.write_bytes(header.ljust(80, b" ") + document[80:])


def _embed_gerber(path: Path, license_text: str) -> None:
    document = path.read_text(encoding="utf-8", errors="strict")
    prefix = "G04 "
    begin = f"{prefix}{BEGIN}*"
    end = f"{prefix}{END}*"
    document = re.sub(
        rf"^{re.escape(begin)}\r?\n.*?^{re.escape(end)}\r?\n?",
        "",
        document,
        flags=re.MULTILINE | re.DOTALL,
    )
    block = "\n".join(
        [begin, *(f"G04 {line}*" for line in license_text.splitlines()), end]
    )
    path.write_text(block + "\n" + document, encoding="utf-8")


def _embed_drill(path: Path, license_text: str) -> None:
    document = path.read_text(encoding="utf-8", errors="strict")
    path.write_text(_replace_text_block(document, "; ", license_text), encoding="utf-8")


def _embed_zip(path: Path, license_text: str) -> None:
    comment = license_text.encode("utf-8")
    if len(comment) > 65535:
        raise ArtifactLicenseMetadataError("ZIP licence comment is too long")
    try:
        with zipfile.ZipFile(path, mode="a") as archive:
            archive.comment = comment
    except zipfile.BadZipFile as error:
        raise ArtifactLicenseMetadataError(f"{path}: invalid ZIP archive") from error


def embed_artifact_license(path: Path, license_text: str | None = None) -> None:
    license_text = (license_text or adjacent_license_text(path)).strip()
    if not _valid_spdx_text(license_text):
        raise ArtifactLicenseMetadataError(f"{path}: incomplete SPDX declaration")
    suffix = artifact_suffix(path)
    handlers = {
        ".drl": _embed_drill,
        ".dxf": _embed_dxf,
        ".gm1": _embed_gerber,
        ".gtl": _embed_gerber,
        ".gto": _embed_gerber,
        ".gts": _embed_gerber,
        ".jpeg": _embed_jpeg,
        ".jpg": _embed_jpeg,
        ".pdf": _embed_pdf,
        ".png": _embed_png,
        ".step": _embed_step,
        ".stl": _embed_stl,
        ".svg": _embed_svg,
        ".zip": _embed_zip,
    }
    try:
        handler = handlers[suffix]
    except KeyError as error:
        raise ArtifactLicenseMetadataError(f"unsupported artifact: {path}") from error
    handler(path, license_text)


def embedded_license_text(path: Path) -> str:
    suffix = artifact_suffix(path)
    if suffix == ".svg":
        document = path.read_text(encoding="utf-8")
        match = re.search(
            r'<metadata id="alphabets-license">(.*?)</metadata>', document, re.DOTALL
        )
        return html.unescape(match.group(1)) if match else ""
    if suffix == ".png":
        for chunk in _png_chunks(path.read_bytes()):
            length = struct.unpack_from(">I", chunk)[0]
            if chunk[4:8] == b"tEXt" and chunk[8 : 8 + length].startswith(b"License\0"):
                return chunk[16 : 8 + length].decode("latin-1")
        return ""
    if suffix in {".jpg", ".jpeg"}:
        document = path.read_bytes()
        if document[2:4] != b"\xff\xfe":
            return ""
        length = struct.unpack_from(">H", document, 4)[0]
        return document[6 : 4 + length].decode("utf-8", errors="replace")
    if suffix == ".pdf":
        document = path.read_bytes()
        return _pdf_info_value(document, b"SPDX") or _pdf_info_value(
            document, b"Subject"
        )
    if suffix == ".step":
        document = path.read_text(encoding="utf-8")
        match = re.search(rf"/\* {BEGIN} \*/(.*?)/\* {END} \*/", document, re.DOTALL)
        return (
            re.sub(r"^/\* | \*/$", "", match.group(1).strip(), flags=re.MULTILINE)
            if match
            else ""
        )
    if suffix == ".dxf":
        document = path.read_text(encoding="utf-8")
        match = re.search(
            rf"^\s*999\r?\n{BEGIN}\r?\n(.*?)^\s*999\r?\n{END}\r?\n",
            document,
            flags=re.MULTILINE | re.DOTALL,
        )
        return (
            re.sub(r"^\s*999\r?\n", "", match.group(1), flags=re.MULTILINE).strip()
            if match
            else ""
        )
    if suffix == ".stl":
        if not _binary_stl(path):
            return ""
        return path.read_bytes()[:80].decode("ascii", errors="replace").strip()
    if suffix in {".gm1", ".gtl", ".gto", ".gts"}:
        document = path.read_text(encoding="utf-8")
        match = re.search(rf"G04 {BEGIN}\*\n(.*?)G04 {END}\*", document, re.DOTALL)
        return (
            re.sub(r"^G04 |\*$", "", match.group(1).strip(), flags=re.MULTILINE)
            if match
            else ""
        )
    if suffix == ".drl":
        document = path.read_text(encoding="utf-8")
        match = re.search(rf"; {BEGIN}\n(.*?); {END}\n", document, re.DOTALL)
        return (
            re.sub(r"^; ", "", match.group(1), flags=re.MULTILINE).strip()
            if match
            else ""
        )
    if suffix == ".zip":
        try:
            with zipfile.ZipFile(path) as archive:
                return archive.comment.decode("utf-8", errors="replace")
        except zipfile.BadZipFile:
            return ""
    return ""


def validate_artifact_license(path: Path) -> None:
    text = embedded_license_text(path)
    if artifact_suffix(path) == ".stl":
        licence_label = "SPDX-License-Identifier:"
        if licence_label not in text or "The Beach Lab" not in text:
            raise ArtifactLicenseMetadataError(f"{path}: incomplete STL header")
    elif not _valid_spdx_text(text):
        raise ArtifactLicenseMetadataError(f"{path}: incomplete embedded SPDX metadata")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="+", type=Path)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    for path in args.paths:
        if args.check:
            validate_artifact_license(path)
        else:
            embed_artifact_license(path)


if __name__ == "__main__":
    main()
# REUSE-IgnoreEnd
