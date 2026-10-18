from __future__ import annotations

import base64
import dataclasses as dc
import io
import json
import logging
import os
import re
from typing import Any, Dict, List, Optional

import pymupdf

from fireflyConverter import data

logger = logging.getLogger(__name__)

BILL_EXTENSIONS: tuple[str, ...] = (".pdf", ".png", ".jpg", ".jpeg", ".webp", ".heic", ".heif")

# Formats the vision model cannot decode itself; they are transcoded before sending.
HEIC_EXTENSIONS: tuple[str, ...] = (".heic", ".heif")

IMAGE_MIME_TYPES: Dict[str, str] = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
}

PDF_TEXT_MIN_CHARS = 20

# Longest side of a transcoded photo, and its JPEG quality. Phone photos are far
# larger than the model needs, and the request would carry megabytes otherwise.
IMAGE_MAX_SIDE = 1600
JPEG_QUALITY = 85

SYSTEM_PROMPT = (
    "You extract structured data from a single invoice or receipt. "
    "Reply only with JSON matching the requested schema. Use ISO dates (YYYY-MM-DD). "
    "'total' is the gross amount to pay. Choose 'category' only from the provided list, "
    "using the exact name, or null if none fits. Choose 'account' only from the provided list, "
    "using the exact name, or null if none fits. Choose 'tags' only from the provided list. "
    "Set 'confidence' between 0 and 1 to reflect how certain the extraction is."
)

BILL_RESPONSE_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "total": {"type": ["number", "null"]},
        "currency": {"type": ["string", "null"]},
        "date": {"type": ["string", "null"]},
        "vendor": {"type": ["string", "null"]},
        "category": {"type": ["string", "null"]},
        "account": {"type": ["string", "null"]},
        "tags": {"type": "array", "items": {"type": "string"}},
        "note": {"type": ["string", "null"]},
        "confidence": {"type": "number"},
    },
    # llama.cpp only guarantees the properties listed here: the local model
    # leaves the others out, and a missing bill date would silently disable the
    # date window of the matcher.
    "required": ["total", "date", "vendor", "category", "account", "tags", "note", "confidence"],
}


class BillExtractionError(Exception):
    """Raised when an LLM response cannot be parsed into a Bill."""


@dc.dataclass
class BillContent:
    """Bill document content prepared for the LLM.

    Exactly one of the two fields is normally set: extracted text for digital
    documents, or a base64 data URI for scans and photos sent to the vision model.

    Attributes:
        text (str | None): Extracted text layer of the document.
        imageDataUri (str | None): Data URI of a rendered or captured image.
    """

    text: Optional[str] = None
    imageDataUri: Optional[str] = None


def discoverBills(directory: str, extensions: tuple[str, ...] = BILL_EXTENSIONS) -> List[str]:
    """List bill files in a directory, sorted by path.

    Subdirectories (such as a processed-bills folder) and hidden files are
    ignored, and files whose extension is not a known bill type are skipped.

    Args:
        directory (str): Directory to scan for bill files.
        extensions (tuple[str, ...]): Accepted file extensions, lowercase.

    Returns:
        List[str]: Sorted paths of the discovered bill files.
    """
    if not os.path.isdir(directory):
        logger.warning(f"Bills directory does not exist: {directory}")
        return []

    found: List[str] = []
    for entry in os.scandir(directory):
        if not entry.is_file() or entry.name.startswith("."):
            continue
        if os.path.splitext(entry.name)[1].lower() in extensions:
            found.append(entry.path)
    return sorted(found)


def readBillContent(path: str, vision: bool = True, maxPages: int = 1) -> BillContent:
    """Read a bill file into text or an image for the LLM.

    Digital PDFs are reduced to their text layer. When that layer is too short
    to be useful, or absent, the first page is rasterized and returned as an
    image so the vision model can read it. Image files are returned directly,
    except HEIC photos, which are transcoded to JPEG because the model server
    cannot decode them.

    Args:
        path (str): Path of the bill file.
        vision (bool): Whether images may be sent to the model, by rasterizing a
            scanned PDF or passing an image file through. Defaults to True.
        maxPages (int): Number of PDF pages to consider for text extraction.

    Returns:
        BillContent: Extracted text or an image data URI.

    Raises:
        BillExtractionError: If the file type is not supported, or the file is an
            image and vision is disabled.
    """
    extension = os.path.splitext(path)[1].lower()

    if extension == ".pdf":
        return _readPdfContent(path, vision, maxPages)

    mimeType = IMAGE_MIME_TYPES.get(extension)
    if mimeType is None and extension not in HEIC_EXTENSIONS:
        raise BillExtractionError(f"Unsupported bill file type: {path}")
    if not vision:
        raise BillExtractionError(f"Vision is disabled but {path} is an image")
    if extension in HEIC_EXTENSIONS:
        return BillContent(imageDataUri=_heicDataUri(path))

    return BillContent(imageDataUri=_toDataUri(_readBytes(path), mimeType))


def _heicDataUri(path: str) -> str:
    """Transcode a HEIC photo into a downscaled JPEG data URI.

    The model server decodes images with a library that cannot read HEIF, so the
    photo is decoded locally, shrunk to a sensible size and re-encoded before it
    is sent. The decoder already applies the rotation that phone photos store as
    metadata rather than as pixels.

    Args:
        path (str): Path of the HEIC photo.

    Returns:
        str: JPEG data URI ready to be sent to the model.

    Raises:
        BillExtractionError: If the optional HEIC dependency is not installed.
    """
    try:
        import pillow_heif
        from PIL import Image
    except ImportError as error:
        raise BillExtractionError(
            f"Reading {path} needs the optional HEIC dependency: "
            "pip install 'firefly-cash-converter[heic]'"
        ) from error

    pillow_heif.register_heif_opener()
    with Image.open(path) as photo:
        photo = photo.convert("RGB")
        photo.thumbnail((IMAGE_MAX_SIDE, IMAGE_MAX_SIDE))
        buffer = io.BytesIO()
        photo.save(buffer, format="JPEG", quality=JPEG_QUALITY)
    return _toDataUri(buffer.getvalue(), "image/jpeg")


def _readPdfContent(path: str, vision: bool, maxPages: int) -> BillContent:
    """Extract a PDF's text layer, falling back to a rendered first page."""
    with pymupdf.open(path) as document:
        text = _extractPdfText(document, maxPages)
        if len(text.strip()) >= PDF_TEXT_MIN_CHARS or not vision or document.page_count == 0:
            return BillContent(text=text)

        pixmap = document.load_page(0).get_pixmap()
        return BillContent(imageDataUri=_toDataUri(pixmap.tobytes("png"), "image/png"))


def _extractPdfText(document: "pymupdf.Document", maxPages: int) -> str:
    """Return the concatenated text of up to maxPages pages."""
    pageCount = min(maxPages, document.page_count)
    return "\n".join(document.load_page(index).get_text() for index in range(pageCount))


def _readBytes(path: str) -> bytes:
    """Read a file's raw bytes."""
    with open(path, "rb") as handle:
        return handle.read()


def _toDataUri(raw: bytes, mimeType: str) -> str:
    """Encode raw bytes as a base64 data URI for the vision API."""
    return f"data:{mimeType};base64,{base64.b64encode(raw).decode('ascii')}"


def buildBillMessages(
    content: BillContent, categories: List[str], tags: List[str], accounts: List[str]
) -> List[Dict[str, Any]]:
    """Build the chat messages that ask the LLM to read one bill.

    Args:
        content (BillContent): Text or image content of the bill.
        categories (List[str]): Category names the model may choose from.
        tags (List[str]): Tag names the model may choose from.
        accounts (List[str]): Account names the model may choose from.

    Returns:
        List[Dict[str, Any]]: System and user messages in OpenAI chat format.
    """
    prompt = _buildUserPrompt(categories, tags, accounts)

    if content.text is not None:
        userContent: Any = f"{prompt}\n\nBill text:\n\"\"\"\n{content.text}\n\"\"\""
    else:
        userContent = [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": content.imageDataUri}},
        ]

    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": userContent},
    ]


def parseBillResponse(path: str, content: str) -> data.Bill:
    """Parse an LLM response into a Bill.

    Args:
        path (str): Path of the source bill file, stored on the result.
        content (str): Raw assistant message content, optionally fenced.

    Returns:
        data.Bill: The extracted bill data.

    Raises:
        BillExtractionError: If the content is not a JSON object.
    """
    try:
        payload = json.loads(_extractJsonObject(content))
    except json.JSONDecodeError as error:
        raise BillExtractionError(f"Could not parse LLM response for {path}: {error}") from error

    if not isinstance(payload, dict):
        raise BillExtractionError(f"LLM response for {path} is not a JSON object")

    confidence = _toFloat(payload.get("confidence"))
    return data.Bill(
        path=path,
        total=_toFloat(payload.get("total")),
        currency=_toStr(payload.get("currency")),
        date=_toStr(payload.get("date")),
        vendor=_toStr(payload.get("vendor")),
        category=_toStr(payload.get("category")),
        account=_toStr(payload.get("account")),
        tags=_toStringList(payload.get("tags")),
        note=_toStr(payload.get("note")),
        confidence=confidence if confidence is not None else 0.0,
    )


class BillReader:
    """Read bills and extract structured data with an LLM.

    Attributes:
        _llm (Any): Chat client exposing a ``chat(messages, response_schema=...)`` method.
        _categories (List[str]): Category names offered to the model.
        _tags (List[str]): Tag names offered to the model.
        _accounts (List[str]): Account names offered to the model.
        _vision (bool): Whether image fallback is allowed for scanned bills.
        _maxPages (int): Number of PDF pages considered for text extraction.
    """

    def __init__(
        self,
        llm: Any,
        categories: List[str],
        tags: List[str],
        accounts: List[str],
        vision: bool = True,
        maxPages: int = 1,
    ) -> None:
        """Initialize the reader.

        Args:
            llm (Any): Chat client (see ``llmInterface.LLMInterface``).
            categories (List[str]): Existing Firefly III category names.
            tags (List[str]): Existing Firefly III tag names.
            accounts (List[str]): Existing Firefly III account names.
            vision (bool): Allow rasterizing scanned bills. Defaults to True.
            maxPages (int): Number of PDF pages to read text from. Defaults to 1.
        """
        self._llm = llm
        self._categories = list(categories)
        self._tags = list(tags)
        self._accounts = list(accounts)
        self._vision = vision
        self._maxPages = maxPages

    def read(self, path: str) -> data.Bill:
        """Read a bill file and return the extracted data.

        Args:
            path (str): Path of the bill file.

        Returns:
            data.Bill: Extracted bill data.

        Raises:
            BillExtractionError: If the file cannot be read or the response parsed.
        """
        logger.info(f"Reading bill: {path}")
        content = readBillContent(path, vision=self._vision, maxPages=self._maxPages)
        messages = buildBillMessages(content, self._categories, self._tags, self._accounts)
        response = self._llm.chat(messages, response_schema=BILL_RESPONSE_SCHEMA)
        return parseBillResponse(path, response)


def _buildUserPrompt(categories: List[str], tags: List[str], accounts: List[str]) -> str:
    """Render the user prompt including the allowed category, tag and account names."""
    categoryList = ", ".join(categories) if categories else "(none defined)"
    tagList = ", ".join(tags) if tags else "(none defined)"
    accountList = ", ".join(accounts) if accounts else "(none defined)"
    return (
        "Read the attached bill and return total, currency, date, vendor, category, "
        "account, tags, note and confidence.\n"
        f"Categories (choose exactly one name or null): {categoryList}\n"
        f"Accounts (choose exactly one name or null): {accountList}\n"
        f"Tags (choose zero or more names): {tagList}"
    )


def _extractJsonObject(content: str) -> str:
    """Strip surrounding prose and code fences, returning the JSON object text."""
    text = content.strip()
    text = re.sub(r"^```[a-zA-Z]*\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end > start:
        return text[start : end + 1]
    return text


def _toFloat(value: Any) -> Optional[float]:
    """Coerce a JSON value to a float, tolerating German decimal formatting."""
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        text = value.strip()
        try:
            return float(text)
        except ValueError:
            pass
        try:
            return float(text.replace(".", "").replace(",", "."))
        except ValueError:
            return None
    return None


def _toStr(value: Any) -> Optional[str]:
    """Coerce a JSON value to a non-empty stripped string or None."""
    if value is None:
        return None
    text = value.strip() if isinstance(value, str) else str(value)
    return text or None


def _toStringList(value: Any) -> List[str]:
    """Coerce a JSON value to a list of non-empty strings."""
    if value is None:
        return []
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    if isinstance(value, (list, tuple)):
        return [str(item).strip() for item in value if str(item).strip()]
    return []
