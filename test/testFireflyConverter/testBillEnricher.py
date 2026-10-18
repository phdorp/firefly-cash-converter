import os
import tempfile
import unittest

from fireflyConverter import billEnricher as be
from fireflyConverter import bills, data


def _write(directory, name, content=""):
    path = os.path.join(directory, name)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(content)
    return path


def _tx(amount, date, description, type="withdrawal"):
    return data.PostTransaction(date=date, amount=amount, description=description, type=type, source_name="barclays")


class _StubReader:
    """Returns scripted bills (or raises scripted errors) keyed by path."""

    def __init__(self, responses):
        self._responses = responses

    def read(self, path):
        result = self._responses[path]
        if isinstance(result, Exception):
            raise result
        return result


class TestBillEnricher(unittest.TestCase):
    def testMatchesAndAppliesBill(self):
        with tempfile.TemporaryDirectory() as directory:
            billPath = _write(directory, "acme.pdf")
            reader = _StubReader(
                {
                    billPath: data.Bill(
                        path=billPath,
                        total=115.0,
                        date="2025-08-01",
                        vendor="money",
                        category="Groceries",
                        tags=[],
                        note="Invoice 7",
                        confidence=0.9,
                    )
                }
            )
            transaction = _tx(115.0, "2025-08-01", "money - Removal")
            enricher = be.BillEnricher(reader, categories=["Groceries"], tags=[], config=be.BillConfig(directory=directory))

            report = enricher.enrich([transaction])

            self.assertEqual(transaction.category_name, "Groceries")
            self.assertEqual(len(report.matched), 1)
            self.assertEqual(report.matched[0].bill_path, billPath)
            self.assertEqual(report.unmatched, [])

    def testReportsUnmatchedBill(self):
        with tempfile.TemporaryDirectory() as directory:
            billPath = _write(directory, "acme.pdf")
            reader = _StubReader({billPath: data.Bill(path=billPath, total=999.0, date="2025-08-01", vendor="money")})
            enricher = be.BillEnricher(reader, categories=[], tags=[], config=be.BillConfig(directory=directory))

            report = enricher.enrich([_tx(115.0, "2025-08-01", "money - Removal")])

            self.assertEqual(report.matched, [])
            self.assertEqual(report.unmatched, [billPath])

    def testReportsAmbiguousBill(self):
        with tempfile.TemporaryDirectory() as directory:
            billPath = _write(directory, "acme.pdf")
            reader = _StubReader({billPath: data.Bill(path=billPath, total=9.99, date="2025-08-01", vendor="Shop")})
            transactions = [_tx(9.99, "2025-08-01", "Shop"), _tx(9.99, "2025-08-02", "Shop")]
            enricher = be.BillEnricher(reader, categories=[], tags=[], config=be.BillConfig(directory=directory))

            report = enricher.enrich(transactions)

            self.assertEqual(report.ambiguous, [billPath])
            self.assertEqual(report.matched, [])

    def testReportsReaderErrors(self):
        with tempfile.TemporaryDirectory() as directory:
            billPath = _write(directory, "broken.pdf")
            reader = _StubReader({billPath: bills.BillExtractionError("boom")})
            enricher = be.BillEnricher(reader, categories=[], tags=[], config=be.BillConfig(directory=directory))

            report = enricher.enrich([_tx(115.0, "2025-08-01", "money - Removal")])

            self.assertEqual(len(report.errors), 1)
            self.assertIn("boom", report.errors[0])

    def testArchiveProcessedMovesAppliedBills(self):
        with tempfile.TemporaryDirectory() as directory:
            billPath = _write(directory, "acme.pdf")
            reader = _StubReader({billPath: data.Bill(path=billPath, total=115.0, date="2025-08-01", vendor="money")})
            config = be.BillConfig(directory=directory, processed_subdir="processed")
            enricher = be.BillEnricher(reader, categories=[], tags=[], config=config)
            report = enricher.enrich([_tx(115.0, "2025-08-01", "money - Removal")])

            enricher.archiveProcessed(report)

            archived = os.path.join(directory, "processed", "acme.pdf")
            self.assertTrue(os.path.exists(archived))
            self.assertFalse(os.path.exists(billPath))

    def testRenderReportListsOutcomes(self):
        report = be.EnrichmentReport(
            matched=[be.MatchRecord(bill_path="/b/a.pdf", description="money - Removal", category="Groceries", tags=["x"])],
            unmatched=["/b/b.pdf"],
            ambiguous=[],
            errors=["/b/c.pdf: boom"],
            issues=["Tag 'y' dropped"],
        )

        text = be.renderReport(report)

        self.assertIn("Matched", text)
        self.assertIn("a.pdf", text)
        self.assertIn("/b/b.pdf", text)
        self.assertIn("boom", text)
        self.assertIn("Tag 'y' dropped", text)


if __name__ == "__main__":
    unittest.main()
