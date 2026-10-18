import base64
import json
import os
import tempfile
import unittest

import pymupdf

from fireflyConverter import bills

# A 1x1 transparent PNG, enough to exercise image handling without image tooling.
_TINY_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
)


def _write(directory, name, content=""):
    path = os.path.join(directory, name)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(content)
    return path


def _writeBytes(directory, name, content):
    path = os.path.join(directory, name)
    with open(path, "wb") as handle:
        handle.write(content)
    return path


def _writePdf(directory, name, text=None):
    path = os.path.join(directory, name)
    document = pymupdf.open()
    page = document.new_page()
    if text:
        page.insert_text((72, 72), text)
    document.save(path)
    document.close()
    return path


class _FakeLlm:
    """Records chat calls and returns a fixed assistant message."""

    def __init__(self, content):
        self._content = content
        self.calls = []

    def chat(self, messages, response_schema=None, temperature=0.0):
        self.calls.append({"messages": messages, "response_schema": response_schema})
        return self._content


class TestBillResponseSchema(unittest.TestCase):
    """Contract tests for the schema the local model is constrained to."""

    def testSchemaRequiresTheFieldsTheMatcherNeeds(self):
        """llama.cpp only guarantees the properties the schema marks as required.

        A local model that is asked for an optional property tends to leave it
        out, and a missing bill date silently disables the date window, so the
        date and the account have to be required to be read back reliably.
        """
        required = bills.BILL_RESPONSE_SCHEMA["required"]

        self.assertIn("date", required)
        self.assertIn("account", required)


class TestParseBillResponse(unittest.TestCase):
    def testParsesCompleteJson(self):
        content = json.dumps(
            {
                "total": 12.34,
                "currency": "EUR",
                "date": "2026-10-01",
                "vendor": "ACME GmbH",
                "category": "Groceries",
                "tags": ["business"],
                "note": "Invoice 42",
                "confidence": 0.9,
            }
        )

        bill = bills.parseBillResponse("bill.pdf", content)

        self.assertEqual(bill.path, "bill.pdf")
        self.assertEqual(bill.total, 12.34)
        self.assertEqual(bill.currency, "EUR")
        self.assertEqual(bill.date, "2026-10-01")
        self.assertEqual(bill.vendor, "ACME GmbH")
        self.assertEqual(bill.category, "Groceries")
        self.assertEqual(bill.tags, ["business"])
        self.assertEqual(bill.note, "Invoice 42")
        self.assertEqual(bill.confidence, 0.9)

    def testStripsMarkdownCodeFences(self):
        content = '```json\n{"total": 1.0, "vendor": "X"}\n```'

        bill = bills.parseBillResponse("bill.pdf", content)

        self.assertEqual(bill.total, 1.0)
        self.assertEqual(bill.vendor, "X")

    def testDefaultsMissingOptionalFields(self):
        bill = bills.parseBillResponse("bill.pdf", "{}")

        self.assertIsNone(bill.total)
        self.assertIsNone(bill.account)
        self.assertEqual(bill.tags, [])
        self.assertEqual(bill.confidence, 0.0)

    def testParsesChosenAccount(self):
        bill = bills.parseBillResponse("bill.pdf", '{"total": 1.0, "account": "Groceries", "confidence": 0.9}')

        self.assertEqual(bill.account, "Groceries")

    def testCoercesNumericStrings(self):
        bill = bills.parseBillResponse("bill.pdf", '{"total": "12.34", "confidence": "0.5"}')

        self.assertEqual(bill.total, 12.34)
        self.assertEqual(bill.confidence, 0.5)

    def testRaisesOnInvalidJson(self):
        with self.assertRaises(bills.BillExtractionError):
            bills.parseBillResponse("bill.pdf", "not json at all")


class TestDiscoverBills(unittest.TestCase):
    def testFindsBillFilesAndSkipsOthersAndProcessed(self):
        with tempfile.TemporaryDirectory() as directory:
            _write(directory, "a.pdf")
            _write(directory, "b.PNG")
            _write(directory, "notes.txt")
            _write(directory, "processed/old.pdf")

            found = bills.discoverBills(directory)

            self.assertEqual(
                found,
                [os.path.join(directory, "a.pdf"), os.path.join(directory, "b.PNG")],
            )

    def testReturnsEmptyListForMissingDirectory(self):
        self.assertEqual(bills.discoverBills("/nonexistent/bills"), [])


class TestBuildBillMessages(unittest.TestCase):
    def testTextContentEmbedsTextAndVocabulary(self):
        content = bills.BillContent(text="Total 12,34 EUR")

        messages = bills.buildBillMessages(content, categories=["Groceries"], tags=["business"], accounts=["Groceries"])

        self.assertEqual(messages[0]["role"], "system")
        self.assertEqual(messages[1]["role"], "user")
        userContent = messages[1]["content"]
        self.assertIsInstance(userContent, str)
        self.assertIn("Groceries", userContent)
        self.assertIn("business", userContent)
        self.assertIn("Total 12,34 EUR", userContent)

    def testTextContentEmbedsAccountVocabulary(self):
        content = bills.BillContent(text="Total 12,34 EUR")

        messages = bills.buildBillMessages(
            content, categories=[], tags=[], accounts=["Assets:Checking", "Restaurants"]
        )

        userContent = messages[1]["content"]
        self.assertIn("Restaurants", userContent)

    def testImageContentAttachesImageUrl(self):
        content = bills.BillContent(imageDataUri="data:image/png;base64,AAAA")

        messages = bills.buildBillMessages(content, categories=[], tags=[], accounts=[])

        userContent = messages[1]["content"]
        self.assertIsInstance(userContent, list)
        imageParts = [part for part in userContent if part["type"] == "image_url"]
        self.assertEqual(len(imageParts), 1)
        self.assertEqual(imageParts[0]["image_url"]["url"], "data:image/png;base64,AAAA")


class TestReadBillContent(unittest.TestCase):
    def testImageFileBecomesDataUri(self):
        with tempfile.TemporaryDirectory() as directory:
            path = _writeBytes(directory, "bill.png", _TINY_PNG)

            content = bills.readBillContent(path)

            self.assertIsNone(content.text)
            self.assertTrue(content.imageDataUri.startswith("data:image/png;base64,"))

    def testPdfWithTextLayerUsesText(self):
        with tempfile.TemporaryDirectory() as directory:
            path = _writePdf(directory, "bill.pdf", text="Invoice total: 12,34 EUR due 2026-10-01")

            content = bills.readBillContent(path)

            self.assertIsNone(content.imageDataUri)
            self.assertIn("12,34", content.text)

    def testScannedPdfFallsBackToImage(self):
        with tempfile.TemporaryDirectory() as directory:
            path = _writePdf(directory, "scan.pdf", text=None)

            content = bills.readBillContent(path)

            self.assertIsNone(content.text)
            self.assertTrue(content.imageDataUri.startswith("data:image/png;base64,"))

    def testUnsupportedTypeRaises(self):
        with tempfile.TemporaryDirectory() as directory:
            path = _write(directory, "bill.txt", "hello")

            with self.assertRaises(bills.BillExtractionError):
                bills.readBillContent(path)

    def testImageFileWithoutVisionRaises(self):
        with tempfile.TemporaryDirectory() as directory:
            path = _writeBytes(directory, "bill.png", _TINY_PNG)

            with self.assertRaises(bills.BillExtractionError):
                bills.readBillContent(path, vision=False)

    def testScannedPdfWithoutVisionReturnsEmptyText(self):
        with tempfile.TemporaryDirectory() as directory:
            path = _writePdf(directory, "scan.pdf", text=None)

            content = bills.readBillContent(path, vision=False)

            self.assertIsNone(content.imageDataUri)
            self.assertEqual(content.text.strip(), "")


class TestBillReader(unittest.TestCase):
    def testReadParsesClientResponseAndSendsSchema(self):
        with tempfile.TemporaryDirectory() as directory:
            path = _writeBytes(directory, "bill.png", _TINY_PNG)
            client = _FakeLlm('{"total": 5.0, "vendor": "Bakery", "category": "Food", "tags": [], "confidence": 0.8}')

            reader = bills.BillReader(client, categories=["Food"], tags=["business"], accounts=[])
            bill = reader.read(path)

            self.assertEqual(bill.path, path)
            self.assertEqual(bill.total, 5.0)
            self.assertEqual(bill.vendor, "Bakery")
            self.assertIs(client.calls[0]["response_schema"], bills.BILL_RESPONSE_SCHEMA)

            userContent = client.calls[0]["messages"][1]["content"]
            self.assertTrue(any(part["type"] == "image_url" for part in userContent))

    def testReadOffersAccountsToTheModel(self):
        with tempfile.TemporaryDirectory() as directory:
            path = _writePdf(directory, "bill.pdf", text="Invoice total: 12,34 EUR due 2026-10-01")
            client = _FakeLlm('{"total": 12.34, "account": "Restaurants", "confidence": 0.7}')

            reader = bills.BillReader(client, categories=[], tags=[], accounts=["Restaurants"])
            bill = reader.read(path)

            self.assertEqual(bill.account, "Restaurants")
            self.assertIn("Restaurants", client.calls[0]["messages"][1]["content"])

    def testReadSendsExtractedTextForDigitalPdf(self):
        with tempfile.TemporaryDirectory() as directory:
            path = _writePdf(directory, "bill.pdf", text="Invoice total: 12,34 EUR due 2026-10-01")
            client = _FakeLlm('{"total": 12.34, "vendor": "ACME", "category": null, "tags": [], "confidence": 0.7}')

            reader = bills.BillReader(client, categories=[], tags=[], accounts=[])
            reader.read(path)

            userContent = client.calls[0]["messages"][1]["content"]
            self.assertIsInstance(userContent, str)
            self.assertIn("12,34", userContent)


if __name__ == "__main__":
    unittest.main()
