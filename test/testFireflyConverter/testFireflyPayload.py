import json
import unittest

from fireflyConverter import data
from fireflyConverter.fireflyPayload import PayloadFactory


def _tx(**overrides):
    """Build a postable transaction with only the required fields set."""
    values = {"date": "2025-01-01", "amount": 10.0, "description": "test", "type": "withdrawal"}
    values.update(overrides)
    return data.PostTransaction(**values)


class TestPayloadFactory(unittest.TestCase):
    def setUp(self) -> None:
        self._factory = PayloadFactory()

    def _postTransaction(self, **kwargs):
        defaults = {
            "type": "withdrawal",
            "date": "2025-01-01T00:00:00",
            "amount": 100.0,
            "description": "test",
        }
        defaults.update(kwargs)
        return self._factory.postTransaction(**defaults)

    def testNanOptionalFieldExcluded(self):
        payload = self._postTransaction(source_name=float("nan"))
        transaction = payload["transactions"][0]
        self.assertNotIn("source_name", transaction)
        json.dumps(payload, allow_nan=False)

    def testNanForeignAmountExcluded(self):
        payload = self._postTransaction(foreign_amount=float("nan"))
        transaction = payload["transactions"][0]
        self.assertNotIn("foreign_amount", transaction)
        json.dumps(payload, allow_nan=False)

    def testZeroForeignAmountPreserved(self):
        payload = self._postTransaction(foreign_amount=0.0)
        self.assertEqual(payload["transactions"][0]["foreign_amount"], 0.0)

    def testZeroIdPreserved(self):
        payload = self._postTransaction(source_id=0)
        self.assertEqual(payload["transactions"][0]["source_id"], 0)

    def testNoneFieldsOmitted(self):
        payload = self._postTransaction(
            source_name=None,
            notes=None,
            currency_code=None,
            foreign_amount=None,
        )
        transaction = payload["transactions"][0]
        for key in ("source_name", "notes", "currency_code", "foreign_amount"):
            self.assertNotIn(key, transaction)

    def testValidOptionalFieldsIncluded(self):
        payload = self._postTransaction(
            source_name="account",
            foreign_amount=42.5,
            notes="note",
        )
        transaction = payload["transactions"][0]
        self.assertEqual(transaction["source_name"], "account")
        self.assertEqual(transaction["foreign_amount"], 42.5)
        self.assertEqual(transaction["notes"], "note")

    def testSplitEntriesAreEmittedInsteadOfOneAggregateEntry(self):
        payload = self._postTransaction(
            currency_code="EUR",
            external_id="source-1",
            reconciled=True,
            splits=[
                {"amount": 40.0, "category_name": "Food", "notes": "first"},
                {"amount": 60.0, "category_name": "Books", "tags": ["bill-matched"]},
            ]
        )

        self.assertEqual([entry["amount"] for entry in payload["transactions"]], ["40.0", "60.0"])
        self.assertEqual(payload["transactions"][0]["category_name"], "Food")
        self.assertEqual(payload["transactions"][1]["tags"], ["bill-matched"])
        for entry in payload["transactions"]:
            self.assertEqual(entry["currency_code"], "EUR")
            self.assertEqual(entry["external_id"], "source-1")
            self.assertTrue(entry["reconciled"])


class TestApplyRules(unittest.TestCase):
    def setUp(self) -> None:
        self._factory = PayloadFactory()

    def testApplyRulesDefaultsToOff(self):
        payload = self._factory.toPayload(_tx())

        self.assertFalse(payload["apply_rules"])

    def testApplyRulesIsThreadedThroughToPayload(self):
        payload = self._factory.toPayload(_tx(), apply_rules=True)

        self.assertTrue(payload["apply_rules"])


if __name__ == "__main__":
    unittest.main()