import unittest

from fireflyConverter import convertData as cvd
from fireflyConverter import loadData as ldb


class TestConvertData(unittest.TestCase):
    def setUp(self) -> None:
        self._loader = ldb.DataLoaderCommon("test/data/common")
        self._transactions = self._loader.load()
        self._converter = cvd.ConvertData(self._transactions, queries="test/config/queries.toml")


class TestFilterByQuery(TestConvertData):
    def testDepositsOnly(self):
        result = self._converter.filterByNamedQuery("deposits_only")
        self.assertEqual(len(result.transactions), 4)
        for transaction in result.transactions:
            self.assertEqual(transaction.type, "deposit")

    def testWithdrawalsOnly(self):
        result = self._converter.filterByNamedQuery("withdrawals_only")
        self.assertEqual(len(result.transactions), 1)
        for transaction in result.transactions:
            self.assertEqual(transaction.type, "withdrawal")

    def testLargeTransactions(self):
        result = self._converter.filterByNamedQuery("large_transactions")
        self.assertEqual(len(result.transactions), 4)
        for transaction in result.transactions:
            self.assertGreater(transaction.amount, 100)

    def testSmallTransactions(self):
        result = self._converter.filterByNamedQuery("small_transactions")
        self.assertEqual(len(result.transactions), 1)
        for transaction in result.transactions:
            self.assertLess(transaction.amount, 100)

    def testMediumTransactions(self):
        result = self._converter.filterByNamedQuery("medium_transactions")
        self.assertEqual(len(result.transactions), 3)
        for transaction in result.transactions:
            self.assertGreaterEqual(transaction.amount, 48.24)
            self.assertLessEqual(transaction.amount, 128.74)

    def testReconciledTransactions(self):
        result = self._converter.filterByNamedQuery("reconciled")
        self.assertEqual(len(result.transactions), 5)
        for transaction in result.transactions:
            self.assertTrue(transaction.reconciled)

    def testContainsInterest(self):
        result = self._converter.filterByNamedQuery("contains_interest")
        self.assertEqual(len(result.transactions), 1)
        self.assertIn("Interest", result.transactions[0].description)

    def testContainsTax(self):
        result = self._converter.filterByNamedQuery("contains_tax")
        self.assertEqual(len(result.transactions), 1)
        self.assertIn("Tax", result.transactions[0].description)

    def testLargeDeposits(self):
        result = self._converter.filterByNamedQuery("large_deposits")
        self.assertEqual(len(result.transactions), 3)
        for transaction in result.transactions:
            self.assertEqual(transaction.type, "deposit")
            self.assertGreater(transaction.amount, 100)

    def testSmallWithdrawals(self):
        result = self._converter.filterByNamedQuery("small_withdrawals")
        self.assertEqual(len(result.transactions), 0)

    def testReconciledLarge(self):
        result = self._converter.filterByNamedQuery("reconciled_large")
        self.assertEqual(len(result.transactions), 4)
        for transaction in result.transactions:
            self.assertTrue(transaction.reconciled)
            self.assertGreater(transaction.amount, 100)

    def testDirectQueryAmountGt500(self):
        result = self._converter.filterByQuery("amount > 500")
        self.assertEqual(len(result.transactions), 1)
        self.assertGreater(result.transactions[0].amount, 500)

    def testSpecificDate(self):
        result = self._converter.filterByNamedQuery("specific_date")
        self.assertEqual(len(result.transactions), 1)
        for transaction in result.transactions:
            self.assertEqual(transaction.date, "2025-12-30T00:00:00")

    def testDateRange(self):
        result = self._converter.filterByNamedQuery("date_range")
        self.assertEqual(len(result.transactions), 4)


class TestFilterByNamedQueries(TestConvertData):
    def testDepositsAndLarge(self):
        result = self._converter.filterByNamedQueries("deposits_only", "large_transactions", logic="and")
        self.assertEqual(len(result.transactions), 3)
        for transaction in result.transactions:
            self.assertEqual(transaction.type, "deposit")
            self.assertGreater(transaction.amount, 100)

    def testDepositsOrWithdrawals(self):
        result = self._converter.filterByNamedQueries("deposits_only", "withdrawals_only", logic="or")
        self.assertEqual(len(result.transactions), 5)

    def testInterestOrTax(self):
        result = self._converter.filterByNamedQueries("contains_interest", "contains_tax", logic="or")
        self.assertEqual(len(result.transactions), 2)
        descriptions = {transaction.description for transaction in result.transactions}
        self.assertTrue(any("Interest" in description for description in descriptions))
        self.assertTrue(any("Tax" in description for description in descriptions))

    def testReconciledAndSmall(self):
        result = self._converter.filterByNamedQueries("reconciled", "small_transactions", logic="and")
        self.assertEqual(len(result.transactions), 1)
        transaction = result.transactions[0]
        self.assertTrue(transaction.reconciled)
        self.assertLess(transaction.amount, 100)

    def testReconciledAndWithdrawal(self):
        result = self._converter.filterByNamedQueries("reconciled", "withdrawals_only", logic="and")
        self.assertEqual(len(result.transactions), 1)
        transaction = result.transactions[0]
        self.assertTrue(transaction.reconciled)
        self.assertEqual(transaction.type, "withdrawal")


class TestFilterByNamedQueryExpression(TestConvertData):
    def testDepositsAndLargeExpression(self):
        expression = ["deposits_only", "and", "large_transactions"]
        result = self._converter.filterByNamedQueryExpression(expression)
        self.assertEqual(len(result.transactions), 3)
        for transaction in result.transactions:
            self.assertEqual(transaction.type, "deposit")
            self.assertGreater(transaction.amount, 100)

    def testDepositsOrWithdrawalsExpression(self):
        expression = ["deposits_only", "or", "withdrawals_only"]
        result = self._converter.filterByNamedQueryExpression(expression)
        self.assertEqual(len(result.transactions), 5)

    def testInterestOrTaxExpression(self):
        expression = ["contains_interest", "or", "contains_tax"]
        result = self._converter.filterByNamedQueryExpression(expression)
        self.assertEqual(len(result.transactions), 2)
        descriptions = {transaction.description for transaction in result.transactions}
        self.assertTrue(any("Interest" in description for description in descriptions))
        self.assertTrue(any("Tax" in description for description in descriptions))

    def testReconciledAndSmallExpression(self):
        expression = ["reconciled", "and", "small_transactions"]
        result = self._converter.filterByNamedQueryExpression(expression)
        self.assertEqual(len(result.transactions), 1)
        transaction = result.transactions[0]
        self.assertTrue(transaction.reconciled)
        self.assertLess(transaction.amount, 100)

    def testReconciledAndWithdrawalExpression(self):
        expression = ["reconciled", "and", "withdrawals_only"]
        result = self._converter.filterByNamedQueryExpression(expression)
        self.assertEqual(len(result.transactions), 1)
        transaction = result.transactions[0]
        self.assertTrue(transaction.reconciled)
        self.assertEqual(transaction.type, "withdrawal")

    def testDepositsLargeAndTaxExpression(self):
        expression = ["deposits_only", "and", "large_transactions", "and", "contains_tax"]
        result = self._converter.filterByNamedQueryExpression(expression)
        self.assertEqual(len(result.transactions), 1)
        transaction = result.transactions[0]
        self.assertEqual(transaction.type, "deposit")
        self.assertGreater(transaction.amount, 100)
        self.assertIn("Tax", transaction.description)


if __name__ == "__main__":
    unittest.main()
