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
            enricher = be.BillEnricher(reader, categories=["Groceries"], tags=[], accounts=[], config=be.BillConfig(directory=directory))

            report = enricher.enrich([transaction])

            self.assertEqual(transaction.category_name, "Groceries")
            self.assertEqual(len(report.matched), 1)
            self.assertEqual(report.matched[0].bill_path, billPath)
            self.assertEqual(report.unmatched, [])

    def testReportListsTheEnrichedTransactions(self):
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
                        confidence=0.9,
                    )
                }
            )
            matchedTx = _tx(115.0, "2025-08-01", "money - Removal")
            untouchedTx = _tx(9.0, "2025-08-02", "coffee")
            enricher = be.BillEnricher(reader, categories=["Groceries"], tags=[], accounts=[], config=be.BillConfig(directory=directory))

            report = enricher.enrich([matchedTx, untouchedTx])

            self.assertEqual(report.matched_transactions, [matchedTx])

    def testReportsUnmatchedBill(self):
        with tempfile.TemporaryDirectory() as directory:
            billPath = _write(directory, "acme.pdf")
            reader = _StubReader({billPath: data.Bill(path=billPath, total=999.0, date="2025-08-01", vendor="money")})
            enricher = be.BillEnricher(reader, categories=[], tags=[], accounts=[], config=be.BillConfig(directory=directory))

            report = enricher.enrich([_tx(115.0, "2025-08-01", "money - Removal")])

            self.assertEqual(report.matched, [])
            self.assertEqual(report.unmatched, [billPath])

    def testReportsAmbiguousBill(self):
        with tempfile.TemporaryDirectory() as directory:
            billPath = _write(directory, "acme.pdf")
            reader = _StubReader({billPath: data.Bill(path=billPath, total=9.99, date="2025-08-01", vendor="Shop")})
            transactions = [_tx(9.99, "2025-08-01", "Shop"), _tx(9.99, "2025-08-02", "Shop")]
            enricher = be.BillEnricher(reader, categories=[], tags=[], accounts=[], config=be.BillConfig(directory=directory))

            report = enricher.enrich(transactions)

            self.assertEqual(report.ambiguous, [billPath])
            self.assertEqual(report.matched, [])

    def testSecondBillForSameTransactionIsReportedAsDuplicate(self):
        with tempfile.TemporaryDirectory() as directory:
            firstPath = _write(directory, "a.pdf")
            secondPath = _write(directory, "b.pdf")
            reader = _StubReader(
                {
                    firstPath: data.Bill(path=firstPath, total=115.0, date="2025-08-01", vendor="money"),
                    secondPath: data.Bill(path=secondPath, total=115.0, date="2025-08-01", vendor="money"),
                }
            )
            enricher = be.BillEnricher(reader, categories=[], tags=[], accounts=[], config=be.BillConfig(directory=directory))

            report = enricher.enrich([_tx(115.0, "2025-08-01", "money - Removal")])

            self.assertEqual(len(report.matched), 1)
            self.assertEqual(report.matched[0].bill_path, firstPath)
            self.assertEqual(report.duplicates, [secondPath])

    def testReportsReaderErrors(self):
        with tempfile.TemporaryDirectory() as directory:
            billPath = _write(directory, "broken.pdf")
            reader = _StubReader({billPath: bills.BillExtractionError("boom")})
            enricher = be.BillEnricher(reader, categories=[], tags=[], accounts=[], config=be.BillConfig(directory=directory))

            report = enricher.enrich([_tx(115.0, "2025-08-01", "money - Removal")])

            self.assertEqual(len(report.errors), 1)
            self.assertIn("boom", report.errors[0])

    def testArchiveProcessedMovesAppliedBills(self):
        with tempfile.TemporaryDirectory() as directory:
            billPath = _write(directory, "acme.pdf")
            reader = _StubReader({billPath: data.Bill(path=billPath, total=115.0, date="2025-08-01", vendor="money")})
            config = be.BillConfig(directory=directory, processed_subdir="processed")
            enricher = be.BillEnricher(reader, categories=[], tags=[], accounts=[], config=config)
            report = enricher.enrich([_tx(115.0, "2025-08-01", "money - Removal")])

            enricher.archiveProcessed(report)

            archived = os.path.join(directory, "processed", "acme.pdf")
            self.assertTrue(os.path.exists(archived))
            self.assertFalse(os.path.exists(billPath))

    def testArchiveProcessedKeepsExistingArchivedFileWithSameName(self):
        with tempfile.TemporaryDirectory() as directory:
            billPath = _write(directory, "acme.pdf", "new")
            os.makedirs(os.path.join(directory, "processed"), exist_ok=True)
            _write(os.path.join(directory, "processed"), "acme.pdf", "old")
            reader = _StubReader({billPath: data.Bill(path=billPath, total=115.0, date="2025-08-01", vendor="money")})
            config = be.BillConfig(directory=directory)
            enricher = be.BillEnricher(reader, categories=[], tags=[], accounts=[], config=config)
            report = enricher.enrich([_tx(115.0, "2025-08-01", "money - Removal")])

            enricher.archiveProcessed(report)

            with open(os.path.join(directory, "processed", "acme.pdf"), encoding="utf-8") as handle:
                self.assertEqual(handle.read(), "old")
            with open(os.path.join(directory, "processed", "acme-1.pdf"), encoding="utf-8") as handle:
                self.assertEqual(handle.read(), "new")
            self.assertFalse(os.path.exists(billPath))

    def testArchiveProcessedCreatesNothingWhenNothingMatched(self):
        with tempfile.TemporaryDirectory() as directory:
            enricher = be.BillEnricher(_StubReader({}), categories=[], tags=[], accounts=[], config=be.BillConfig(directory=directory))

            enricher.archiveProcessed(be.EnrichmentReport())

            self.assertFalse(os.path.exists(os.path.join(directory, "processed")))

    def testReportListsTheChosenCounterAccount(self):
        with tempfile.TemporaryDirectory() as directory:
            billPath = _write(directory, "acme.pdf")
            reader = _StubReader(
                {
                    billPath: data.Bill(
                        path=billPath,
                        total=115.0,
                        date="2025-08-01",
                        vendor="money",
                        account="Restaurants",
                        confidence=0.9,
                    )
                }
            )
            transaction = _tx(115.0, "2025-08-01", "money - Removal")
            enricher = be.BillEnricher(
                reader, categories=[], tags=[], accounts=["Restaurants"], config=be.BillConfig(directory=directory)
            )

            report = enricher.enrich([transaction])

            self.assertEqual(transaction.destination_name, "Restaurants")
            self.assertEqual(report.matched[0].account, "Restaurants")

    def testCollectsUnknownAccountsForCreation(self):
        with tempfile.TemporaryDirectory() as directory:
            billPath = _write(directory, "acme.pdf")
            reader = _StubReader(
                {
                    billPath: data.Bill(
                        path=billPath,
                        total=115.0,
                        date="2025-08-01",
                        vendor="money",
                        account="New merchant",
                        confidence=0.9,
                    )
                }
            )
            transaction = _tx(115.0, "2025-08-01", "money - Removal")
            enricher = be.BillEnricher(
                reader, categories=[], tags=[], accounts=["Existing"], config=be.BillConfig(directory=directory)
            )

            report = enricher.enrich([transaction])
            self.assertIsNone(transaction.destination_name)
            self.assertFalse(hasattr(report, "new_accounts"))

    def testReportsAdditionalBillsOnASplit(self):
        with tempfile.TemporaryDirectory() as directory:
            firstPath = _write(directory, "one.pdf")
            secondPath = _write(directory, "two.pdf")
            reader = _StubReader(
                {
                    firstPath: data.Bill(
                        path=firstPath,
                        total=40.0,
                        date="2025-08-01",
                        vendor="money",
                        category="Food",
                        confidence=0.9,
                    ),
                    secondPath: data.Bill(
                        path=secondPath,
                        total=75.0,
                        date="2025-08-01",
                        vendor="money",
                        category="Books",
                        confidence=0.9,
                    ),
                }
            )
            transaction = _tx(115.0, "2025-08-01", "money - Removal")
            enricher = be.BillEnricher(
                reader, categories=["Food", "Books"], tags=[], accounts=[], config=be.BillConfig(directory=directory)
            )

            report = enricher.enrich([transaction])

            self.assertEqual(len(report.matched), 1)
            self.assertEqual([bill.path for bill in report.matched[0].additional_bills], [secondPath])
            self.assertEqual(report.ambiguous, [])
            self.assertEqual([split.amount for split in transaction.split_transactions], [40.0, 75.0])

    def testRenderReportListsOutcomes(self):
        report = be.EnrichmentReport(
            matched=[
                be.MatchRecord(
                    bill_path="/b/a.pdf",
                    description="money - Removal",
                    category="Groceries",
                    account="Restaurants",
                    tags=["x"],
                )
            ],
            unmatched=["/b/b.pdf"],
            ambiguous=[],
            duplicates=["/b/d.pdf"],
            errors=["/b/c.pdf: boom"],
            issues=["Tag 'y' dropped"],
        )

        text = be.renderReport(report)

        self.assertIn("Matched", text)
        self.assertIn("a.pdf", text)
        self.assertIn("Restaurants", text)
        self.assertIn("/b/b.pdf", text)
        self.assertIn("/b/d.pdf", text)
        self.assertIn("boom", text)
        self.assertIn("Tag 'y' dropped", text)

    def testRenderReportVerboseIncludesLlmResponse(self):
        report = be.EnrichmentReport(
            matched=[
                be.MatchRecord(
                    bill_path="/b/a.pdf",
                    description="money - Removal",
                    category="Groceries",
                    account="Restaurants",
                    tags=["x"],
                    llm_response='{"total": 115.0, "vendor": "money"}',
                )
            ],
            unmatched=[],
            ambiguous=[],
            duplicates=[],
            errors=[],
            issues=[],
        )

        verbose = be.renderReport(report, verbose=True)
        self.assertIn("money - Removal", verbose)
        self.assertIn('"total": 115.0', verbose)

        compact = be.renderReport(report, verbose=False)
        self.assertNotIn('"total": 115.0', compact)

    def testRenderReportVerboseIncludesUnmatchedLlmResponse(self):
        report = be.EnrichmentReport(
            unmatched=["/b/unmatched.pdf"],
            llm_responses={"/b/unmatched.pdf": '{"total": 3.0, "vendor": "Cafe"}'},
        )

        verbose = be.renderReport(report, verbose=True)

        self.assertIn("/b/unmatched.pdf", verbose)
        self.assertIn('LLM: {"total": 3.0, "vendor": "Cafe"}', verbose)


if __name__ == "__main__":
    unittest.main()
