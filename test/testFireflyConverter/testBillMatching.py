import unittest

from fireflyConverter import billMatching as bm
from fireflyConverter import data


def _tx(amount, date, description, type="withdrawal"):
    return data.PostTransaction(date=date, amount=amount, description=description, type=type, source_name="barclays")


def _bill(path="/bills/acme.pdf", **kwargs):
    return data.Bill(path=path, **kwargs)


class TestVendorSimilarity(unittest.TestCase):
    def testVendorContainedInDescriptionScoresHigh(self):
        self.assertGreaterEqual(bm.vendorSimilarity("ACME GmbH", "ACME GmbH Berlin 10115"), 0.6)

    def testUnrelatedVendorScoresLow(self):
        self.assertLess(bm.vendorSimilarity("ACME GmbH", "REWE Supermarkt"), 0.6)

    def testEmptyVendorScoresZero(self):
        self.assertEqual(bm.vendorSimilarity("", "anything"), 0.0)


class TestBillMatcher(unittest.TestCase):
    def testMatchesUniqueTransactionByAmountDateVendor(self):
        transaction = _tx(12.34, "2026-10-01", "ACME GmbH")
        matcher = bm.BillMatcher([transaction])

        outcome = matcher.match(_bill(total=12.34, date="2026-10-01", vendor="ACME GmbH", confidence=0.9))

        self.assertEqual(outcome.status, "matched")
        self.assertIs(outcome.transaction, transaction)

    def testBillWithoutTotalIsNotMatched(self):
        matcher = bm.BillMatcher([_tx(12.34, "2026-10-01", "ACME GmbH")])

        outcome = matcher.match(_bill(total=None, date="2026-10-01", vendor="ACME GmbH"))

        self.assertEqual(outcome.status, "no_total")
        self.assertIsNone(outcome.transaction)

    def testMultipleAmountCandidatesAreAmbiguous(self):
        transactions = [_tx(9.99, "2026-10-01", "Shop"), _tx(9.99, "2026-10-02", "Shop")]
        matcher = bm.BillMatcher(transactions)

        outcome = matcher.match(_bill(total=9.99, date="2026-10-01", vendor="Shop"))

        self.assertEqual(outcome.status, "ambiguous")
        self.assertIsNone(outcome.transaction)

    def testDissimilarVendorIsNotMatched(self):
        matcher = bm.BillMatcher([_tx(9.99, "2026-10-01", "REWE Supermarkt")])

        outcome = matcher.match(_bill(total=9.99, date="2026-10-01", vendor="ACME GmbH"))

        self.assertEqual(outcome.status, "no_candidate")

    def testTransactionOutsideDateWindowIsNotMatched(self):
        matcher = bm.BillMatcher([_tx(12.34, "2026-01-01", "ACME GmbH")])

        outcome = matcher.match(_bill(total=12.34, date="2026-10-01", vendor="ACME GmbH"))

        self.assertEqual(outcome.status, "no_candidate")

    def testDepositsAreNotCandidates(self):
        deposit = _tx(12.34, "2026-10-01", "ACME GmbH", type="deposit")
        matcher = bm.BillMatcher([deposit])

        outcome = matcher.match(_bill(total=12.34, date="2026-10-01", vendor="ACME GmbH"))

        self.assertEqual(outcome.status, "no_candidate")

    def testAmountToleranceAllowsSmallDifference(self):
        transaction = _tx(12.30, "2026-10-01", "ACME GmbH")

        strict = bm.BillMatcher([transaction], amountTolerance=0.0)
        lenient = bm.BillMatcher([transaction], amountTolerance=0.05)

        self.assertEqual(strict.match(_bill(total=12.34, date="2026-10-01", vendor="ACME")).status, "no_candidate")
        self.assertEqual(lenient.match(_bill(total=12.34, date="2026-10-01", vendor="ACME")).status, "matched")

    def testMatchedTransactionIsNotHandedToASecondBill(self):
        transaction = _tx(12.34, "2026-10-01", "ACME GmbH")
        matcher = bm.BillMatcher([transaction])

        first = matcher.match(_bill(path="/bills/one.pdf", total=12.34, date="2026-10-01", vendor="ACME GmbH"))
        second = matcher.match(_bill(path="/bills/two.pdf", total=12.34, date="2026-10-01", vendor="ACME GmbH"))

        self.assertEqual(first.status, "matched")
        self.assertIs(first.transaction, transaction)
        self.assertEqual(second.status, "already_matched")
        self.assertIsNone(second.transaction)

    def testSecondBillTakesTheRemainingUnclaimedTransaction(self):
        firstTransaction = _tx(9.99, "2026-10-01", "Shop")
        secondTransaction = _tx(9.99, "2026-10-02", "Shop")
        matcher = bm.BillMatcher([firstTransaction, secondTransaction])

        first = matcher.match(_bill(path="/bills/one.pdf", total=9.99, date="2026-10-01", vendor="Shop"))
        second = matcher.match(_bill(path="/bills/two.pdf", total=9.99, date="2026-10-02", vendor="Shop"))

        self.assertEqual(first.status, "ambiguous")
        self.assertEqual(second.status, "ambiguous")


class TestApplyBill(unittest.TestCase):
    def testSetsCanonicalCategoryTagsAndNotes(self):
        transaction = _tx(12.34, "2026-10-01", "ACME GmbH")
        bill = _bill(category="groceries", tags=["Business"], note="Invoice 42", confidence=0.9)

        issues = bm.applyBill(
            bill,
            transaction,
            categories=["Groceries"],
            tags=["business"],
            markerTag="bill-matched",
            confidenceThreshold=0.5,
        )

        self.assertEqual(transaction.category_name, "Groceries")
        self.assertEqual(transaction.tags, ["business", "bill-matched"])
        self.assertIn("Invoice 42", transaction.notes)
        self.assertIn("acme.pdf", transaction.notes)
        self.assertEqual(issues, [])

    def testUnknownCategoryIsDroppedAndReported(self):
        transaction = _tx(12.34, "2026-10-01", "ACME GmbH")
        bill = _bill(category="Travel", tags=[], note=None, confidence=0.9)

        issues = bm.applyBill(bill, transaction, categories=["Groceries"], tags=[], markerTag="bill-matched")

        self.assertIsNone(transaction.category_name)
        self.assertTrue(any("Travel" in issue for issue in issues))

    def testUnknownTagIsDroppedAndReported(self):
        transaction = _tx(12.34, "2026-10-01", "ACME GmbH")
        bill = _bill(category=None, tags=["nonsense"], note=None, confidence=0.9)

        issues = bm.applyBill(bill, transaction, categories=[], tags=["business"], markerTag="bill-matched")

        self.assertEqual(transaction.tags, ["bill-matched"])
        self.assertTrue(any("nonsense" in issue for issue in issues))

    def testLowConfidenceSkipsCategoryAndTags(self):
        transaction = _tx(12.34, "2026-10-01", "ACME GmbH")
        bill = _bill(category="Groceries", tags=["business"], note="Invoice 42", confidence=0.2)

        issues = bm.applyBill(
            bill,
            transaction,
            categories=["Groceries"],
            tags=["business"],
            markerTag="bill-matched",
            confidenceThreshold=0.5,
        )

        self.assertIsNone(transaction.category_name)
        self.assertEqual(transaction.tags, ["bill-matched"])
        self.assertTrue(any("confidence" in issue.lower() for issue in issues))

    def testNotesAreAppendedToExistingNotes(self):
        transaction = _tx(12.34, "2026-10-01", "ACME GmbH")
        transaction.notes = "existing note"
        bill = _bill(category=None, tags=[], note="Invoice 42", confidence=0.9)

        bm.applyBill(bill, transaction, categories=[], tags=[])

        self.assertIn("existing note", transaction.notes)
        self.assertIn("Invoice 42", transaction.notes)


if __name__ == "__main__":
    unittest.main()
