from __future__ import annotations

import base64
import dataclasses as dc
import io
import json
import logging
import os
import re
import tempfile
from contextlib import contextmanager
from typing import Any, Dict, Iterator, List, Optional

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
EXAMPLE_METADATA_EXTENSION = ".json"

SYSTEM_PROMPT = (
    "You extract structured data from a single invoice or receipt. "
    "Reply only with JSON matching the requested schema. Use ISO dates (YYYY-MM-DD). "
    "'total' is the gross amount to pay. Choose 'category' only from the provided list, "
    "using the exact name, or null if none fits. Choose 'account' from the provided list "
    "using the exact name, or null if none fits. "
    "Choose 'tags' only from the provided list. If multiple bills match one transaction, "
    "each bill contributes its own category, tags and note. "
    "You may use the 'splits' field for distinct bill positions when splitting them "
    "produces a materially better match to the provided categories or tags. "
    "Prefer the fewest splits possible: do not split when one allocation is sufficient, "
    "and combine positions that have the same suitable category and tags. "
    "Never return more split entries than the configured maximum. "
    "Positive examples show desired behavior; negative examples show behavior to avoid. "
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
        "splits": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "amount": {"type": ["number", "null"]},
                    "category": {"type": ["string", "null"]},
                    "tags": {"type": "array", "items": {"type": "string"}},
                    "note": {"type": ["string", "null"]},
                    "confidence": {"type": "number"},
                },
                "required": ["amount", "category", "tags", "note", "confidence"],
            },
        },
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


@dc.dataclass
class PromptExample:
    """One bill input and its expected structured response."""

    name: str
    kind: str
    content: BillContent
    response: Dict[str, Any]


def loadPromptExamples(
    directory: str | None,
    maxSplits: int = 5,
    renderResolution: int = IMAGE_MAX_SIDE,
) -> List[PromptExample]:
    """Load prompt examples from metadata JSON files in a directory."""
    if not directory:
        return []
    if not os.path.isdir(directory):
        raise BillExtractionError(f"Prompt examples directory does not exist: {directory}")

    examples: List[PromptExample] = []
    for kind in ("positive", "negative"):
        kindDirectory = os.path.join(directory, kind)
        if not os.path.isdir(kindDirectory):
            continue
        for metadataPath in sorted(discoverBills(kindDirectory, (EXAMPLE_METADATA_EXTENSION,))):
            try:
                with open(metadataPath, encoding="utf-8") as handle:
                    metadata = json.load(handle)
                inputPath = metadata["input"]
                response = metadata["response"]
                if not isinstance(inputPath, str) or not isinstance(response, dict):
                    raise ValueError("'input' must be a string and 'response' must be an object")
                if any(field not in response for field in BILL_RESPONSE_SCHEMA["required"]):
                    raise ValueError("response is missing a required bill field")
                rawSplits = response.get("splits", [])
                if not isinstance(rawSplits, list) or len(rawSplits) > maxSplits:
                    raise ValueError(f"response must contain at most {maxSplits} split entries")
                inputFile = os.path.join(kindDirectory, inputPath)
                if os.path.splitext(inputFile)[1].lower() in (".txt", ".md"):
                    with open(inputFile, encoding="utf-8") as handle:
                        content = BillContent(text=handle.read())
                else:
                    content = readBillContent(inputFile, renderResolution=renderResolution)
                examples.append(PromptExample(os.path.basename(metadataPath), kind, content, response))
            except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError, BillExtractionError) as error:
                raise BillExtractionError(f"Invalid {kind} prompt example {metadataPath}: {error}") from error
    return examples


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


def readBillContent(
    path: str,
    vision: bool = True,
    maxPages: int = 1,
    renderResolution: int = IMAGE_MAX_SIDE,
) -> BillContent:
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
        renderResolution (int): Maximum pixel length of a rendered image side.

    Returns:
        BillContent: Extracted text or an image data URI.

    Raises:
        BillExtractionError: If the file type is not supported, or the file is an
            image and vision is disabled.
    """
    if renderResolution <= 0:
        raise BillExtractionError("renderResolution must be greater than zero")
    extension = os.path.splitext(path)[1].lower()

    if extension == ".pdf":
        return _readPdfContent(path, vision, maxPages, renderResolution)

    mimeType = IMAGE_MIME_TYPES.get(extension)
    if mimeType is None and extension not in HEIC_EXTENSIONS:
        raise BillExtractionError(f"Unsupported bill file type: {path}")
    if not vision:
        raise BillExtractionError(f"Vision is disabled but {path} is an image")
    if extension in HEIC_EXTENSIONS:
        return BillContent(imageDataUri=_heicDataUri(path, renderResolution))

    return BillContent(imageDataUri=_imageDataUri(path, mimeType, renderResolution))


def _heicDataUri(path: str, renderResolution: int = IMAGE_MAX_SIDE) -> str:
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
        photo.thumbnail((renderResolution, renderResolution))
        buffer = io.BytesIO()
        photo.save(buffer, format="JPEG", quality=JPEG_QUALITY)
    return _toDataUri(buffer.getvalue(), "image/jpeg")


def _readPdfContent(path: str, vision: bool, maxPages: int, renderResolution: int) -> BillContent:
    """Extract a PDF's text layer, falling back to a rendered first page."""
    with pymupdf.open(path) as document:
        text = _extractPdfText(document, maxPages)
        if len(text.strip()) >= PDF_TEXT_MIN_CHARS or not vision or document.page_count == 0:
            return BillContent(text=text)

        return BillContent(imageDataUri=_renderedImageDataUri(document.load_page(0), renderResolution))


def _imageDataUri(path: str, mimeType: str, renderResolution: int) -> str:
    """Return an image as-is when small enough, otherwise render it as PNG."""
    try:
        pixmap = pymupdf.Pixmap(path)
    except pymupdf.mupdf.FzErrorFormat:
        return _toDataUri(_readBytes(path), mimeType)
    if max(pixmap.width, pixmap.height) <= renderResolution:
        return _toDataUri(_readBytes(path), mimeType)
    with pymupdf.open(path) as document:
        return _renderedImageDataUri(document.load_page(0), renderResolution)


def _renderedImageDataUri(page: "pymupdf.Page", renderResolution: int) -> str:
    """Render a page so its longest side does not exceed renderResolution."""
    if renderResolution <= 0:
        raise ValueError("renderResolution must be greater than zero")
    source = page.get_pixmap()
    scale = min(1.0, renderResolution / max(source.width, source.height))
    pixmap = page.get_pixmap(matrix=pymupdf.Matrix(scale, scale))
    return _toDataUri(pixmap.tobytes("png"), "image/png")


def _extractPdfText(document: "pymupdf.Document", maxPages: int) -> str:
    """Return the concatenated text of up to maxPages pages."""
    pageCount = min(maxPages, document.page_count)
    return "\n".join(document.load_page(index).get_text() for index in range(pageCount))


def _readBytes(path: str) -> bytes:
    """Read a file's raw bytes."""
    with open(path, "rb") as handle:
        return handle.read()


@contextmanager
def prepareBillUpload(path: str, renderResolution: int = IMAGE_MAX_SIDE) -> Iterator[tuple[str, str]]:
    """Prepare a bill file for Firefly attachment upload.

    PDFs are uploaded unchanged. Image files are rendered to bounded JPEGs in
    a temporary file; the source file is never modified.

    Args:
        path (str): Source bill path.
        renderResolution (int): Maximum pixel length of the rendered image side.

    Yields:
        tuple[str, str]: Upload path and filename.

    Raises:
        BillExtractionError: If an image cannot be converted to JPEG.
    """
    extension = os.path.splitext(path)[1].lower()
    if extension == ".pdf":
        yield path, os.path.basename(path)
        return
    if extension not in IMAGE_MIME_TYPES and extension not in HEIC_EXTENSIONS:
        raise BillExtractionError(f"Unsupported bill file type: {path}")
    if renderResolution <= 0:
        raise BillExtractionError("renderResolution must be greater than zero")

    temporaryPath: Optional[str] = None
    try:
        if extension in HEIC_EXTENSIONS:
            raw = _heicJpegBytes(path, renderResolution)
        else:
            try:
                with pymupdf.open(path) as document:
                    page = document.load_page(0)
                    source = page.get_pixmap()
                    scale = min(1.0, renderResolution / max(source.width, source.height))
                    pixmap = page.get_pixmap(matrix=pymupdf.Matrix(scale, scale), alpha=False)
                    raw = pixmap.tobytes("jpg", jpg_quality=JPEG_QUALITY)
            except (pymupdf.mupdf.FzErrorFormat, RuntimeError) as error:
                raise BillExtractionError(f"Could not convert image {path} to JPEG: {error}") from error

        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as handle:
            handle.write(raw)
            temporaryPath = handle.name
        yield temporaryPath, f"{os.path.splitext(os.path.basename(path))[0]}.jpg"
    finally:
        if temporaryPath is not None:
            try:
                os.unlink(temporaryPath)
            except FileNotFoundError:
                pass


def _heicJpegBytes(path: str, renderResolution: int) -> bytes:
    """Convert a HEIC image to bounded JPEG bytes."""
    try:
        import pillow_heif
        from PIL import Image
    except ImportError as error:
        raise BillExtractionError(
            f"Uploading {path} needs the optional HEIC dependency: "
            "pip install 'firefly-cash-converter[heic]'"
        ) from error

    pillow_heif.register_heif_opener()
    with Image.open(path) as photo:
        photo = photo.convert("RGB")
        photo.thumbnail((renderResolution, renderResolution))
        buffer = io.BytesIO()
        photo.save(buffer, format="JPEG", quality=JPEG_QUALITY)
        return buffer.getvalue()


def _toDataUri(raw: bytes, mimeType: str) -> str:
    """Encode raw bytes as a base64 data URI for the vision API."""
    return f"data:{mimeType};base64,{base64.b64encode(raw).decode('ascii')}"


def buildBillMessages(
    content: BillContent,
    categories: List[str],
    tags: List[str],
    accounts: List[str],
    maxSplits: int = 5,
    examples: List[PromptExample] | None = None,
) -> List[Dict[str, Any]]:
    """Build the chat messages that ask the LLM to read one bill.

    Args:
        content (BillContent): Text or image content of the bill.
        categories (List[str]): Category names the model may choose from.
        tags (List[str]): Tag names the model may choose from.
        accounts (List[str]): Account names the model may choose from.
        maxSplits (int): Maximum number of split entries the model may return.
        examples (List[PromptExample] | None): Few-shot bill/response examples.

    Returns:
        List[Dict[str, Any]]: System and user messages in OpenAI chat format.
    """
    prompt = _buildUserPrompt(categories, tags, accounts, maxSplits)
    examples = examples or []
    exampleText = _renderExampleText(examples)

    if content.text is not None:
        userContent: Any = _buildTextUserContent(prompt, exampleText, content.text, examples)
    else:
        userContent = _buildMultimodalUserContent(prompt, content, examples)

    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": userContent},
    ]


def parseBillResponse(path: str, content: str, *, raw_response: str | None = None) -> data.Bill:
    """Parse an LLM response into a Bill.

    Args:
        path (str): Path of the source bill file, stored on the result.
        content (str): Raw assistant message content, optionally fenced.
        raw_response (str | None): Original LLM response for verbose reporting.

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
    rawSplits = payload.get("splits")
    splits = [
        data.BillSplit(
            amount=_toFloat(item.get("amount")),
            category=_toStr(item.get("category")),
            tags=_toStringList(item.get("tags")),
            note=_toStr(item.get("note")),
            confidence=_toFloat(item.get("confidence")) or 0.0,
        )
        for item in (rawSplits if isinstance(rawSplits, list) else [])
        if isinstance(item, dict)
    ]
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
        splits=splits,
        llm_response=raw_response,
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
        _renderResolution (int): Maximum pixel length of a rendered image side.
        _maxSplits (int): Maximum number of split entries requested from the model.
    """

    def __init__(
        self,
        llm: Any,
        categories: List[str],
        tags: List[str],
        accounts: List[str],
        vision: bool = True,
        maxPages: int = 1,
        renderResolution: int = IMAGE_MAX_SIDE,
        maxSplits: int = 5,
        examples: List[PromptExample] | None = None,
    ) -> None:
        """Initialize the reader.

        Args:
            llm (Any): Chat client (see ``llmInterface.LLMInterface``).
            categories (List[str]): Existing Firefly III category names.
            tags (List[str]): Existing Firefly III tag names.
            accounts (List[str]): Existing Firefly III account names.
            vision (bool): Allow rasterizing scanned bills. Defaults to True.
            maxPages (int): Number of PDF pages to read text from. Defaults to 1.
            renderResolution (int): Maximum pixel length of a rendered image side.
            maxSplits (int): Maximum number of split entries to request. Defaults to 5.
            examples (List[PromptExample] | None): Few-shot examples for the model.
        """
        self._llm = llm
        self._categories = list(categories)
        self._tags = list(tags)
        self._accounts = list(accounts)
        self._vision = vision
        self._maxPages = maxPages
        self._renderResolution = renderResolution
        self._maxSplits = max(1, maxSplits)
        self._examples = list(examples or [])

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
        content = readBillContent(
            path,
            vision=self._vision,
            maxPages=self._maxPages,
            renderResolution=self._renderResolution,
        )
        messages = buildBillMessages(
            content,
            self._categories,
            self._tags,
            self._accounts,
            maxSplits=self._maxSplits,
            examples=self._examples,
        )
        response = self._llm.chat(messages, response_schema=BILL_RESPONSE_SCHEMA)
        return parseBillResponse(path, response, raw_response=response)


def _buildUserPrompt(categories: List[str], tags: List[str], accounts: List[str], maxSplits: int) -> str:
    """Render the user prompt including the allowed category, tag and account names."""
    categoryList = ", ".join(categories) if categories else "(none defined)"
    tagList = ", ".join(tags) if tags else "(none defined)"
    accountList = ", ".join(accounts) if accounts else "(none defined)"
    return (
        "Read the attached bill and return total, currency, date, vendor, category, "
        "account, tags, note and confidence.\n"
        f"Categories (choose exactly one name or null): {categoryList}\n"
        f"Accounts (choose exactly one existing name or null): {accountList}\n"
        f"Tags (choose zero or more names): {tagList}\n"
        "If multiple bills match one split transaction, each bill contributes its own category, tags and note."
        " If bill positions need different categories or tags, use the fewest possible "
        f"entries in 'splits' (maximum {maxSplits}); leave it empty when one allocation is sufficient."
    )


def _renderExampleText(examples: List[PromptExample]) -> str:
    """Render text portions of few-shot examples."""
    parts = ["\n\nExamples of bill extractions (positive examples are desired; negative examples are to be avoided):"]
    for index, example in enumerate(examples, start=1):
        label = "desired positive" if example.kind == "positive" else "negative to avoid"
        parts.append(
            f"\nExample {index} ({label}, {example.name}) response:\n"
            f"{json.dumps(example.response, ensure_ascii=False)}"
        )
        if example.content.text is not None:
            parts.append(f"Example {index} bill text:\n\"\"\"\n{example.content.text}\n\"\"\"")
        else:
            parts.append(f"Example {index} bill image is attached below.")
    return "\n".join(parts)


def _buildTextUserContent(
    prompt: str, exampleText: str, billText: str, examples: List[PromptExample]
) -> str | List[Dict[str, Any]]:
    """Build text-only or multimodal content when examples include images."""
    imageExamples = [example for example in examples if example.content.imageDataUri]
    if not imageExamples:
        return f"{prompt}{exampleText}\n\nBill text:\n\"\"\"\n{billText}\n\"\"\""
    return _buildMultimodalUserContent(prompt, BillContent(text=billText), examples)


def _buildMultimodalUserContent(
    prompt: str, content: BillContent, examples: List[PromptExample]
) -> List[Dict[str, Any]]:
    """Build user content parts for examples and the current bill."""
    parts: List[Dict[str, Any]] = [{"type": "text", "text": prompt}]
    for index, example in enumerate(examples, start=1):
        label = "desired positive" if example.kind == "positive" else "negative to avoid"
        parts.append(
            {
                "type": "text",
                "text": (
                    f"\nExample {index} ({label}, {example.name}) response:\n"
                    f"{json.dumps(example.response, ensure_ascii=False)}"
                ),
            }
        )
        if example.content.text is not None:
            parts.append(
                {
                    "type": "text",
                    "text": f"Example {index} bill text:\n\"\"\"\n{example.content.text}\n\"\"\"",
                }
            )
        if example.content.imageDataUri:
            parts.append(
                {
                    "type": "text",
                    "text": f"Example {index} bill image:",
                }
            )
            parts.append(
                {"type": "image_url", "image_url": {"url": example.content.imageDataUri}}
            )
    if content.text is not None:
        parts.append({"type": "text", "text": f"\nCurrent bill text:\n\"\"\"\n{content.text}\n\"\"\""})
    else:
        parts.append({"type": "text", "text": "\nCurrent bill image is attached below."})
        parts.append({"type": "image_url", "image_url": {"url": content.imageDataUri}})
    return parts


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
