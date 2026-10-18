import json
import os
import tempfile
import unittest

from fireflyConverter import bills


def _write(directory, name, content=""):
    path = os.path.join(directory, name)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(content)
    return path


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
        self.assertEqual(bill.tags, [])
        self.assertEqual(bill.confidence, 0.0)

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

        messages = bills.buildBillMessages(content, categories=["Groceries"], tags=["business"])

        self.assertEqual(messages[0]["role"], "system")
        self.assertEqual(messages[1]["role"], "user")
        userContent = messages[1]["content"]
        self.assertIsInstance(userContent, str)
        self.assertIn("Groceries", userContent)
        self.assertIn("business", userContent)
        self.assertIn("Total 12,34 EUR", userContent)

    def testImageContentAttachesImageUrl(self):
        content = bills.BillContent(imageDataUri="data:image/png;base64,AAAA")

        messages = bills.buildBillMessages(content, categories=[], tags=[])

        userContent = messages[1]["content"]
        self.assertIsInstance(userContent, list)
        imageParts = [part for part in userContent if part["type"] == "image_url"]
        self.assertEqual(len(imageParts), 1)
        self.assertEqual(imageParts[0]["image_url"]["url"], "data:image/png;base64,AAAA")


if __name__ == "__main__":
    unittest.main()
