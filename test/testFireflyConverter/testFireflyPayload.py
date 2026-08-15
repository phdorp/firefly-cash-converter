import json
import unittest

from fireflyConverter.fireflyPayload import PayloadFactory


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


if __name__ == "__main__":
    unittest.main()