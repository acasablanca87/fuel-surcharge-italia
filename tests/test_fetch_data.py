import unittest

from fetch_data import DataValidationError, parse_float, validate_price_components


class FetchDataTests(unittest.TestCase):
    def test_parse_float_converts_mase_euros_per_thousand_litres(self):
        self.assertEqual(parse_float("2115,1", "PREZZO"), 2.1151)

    def test_parse_float_rejects_missing_and_invalid_values(self):
        for value in (None, "", "not-a-number"):
            with self.subTest(value=value):
                with self.assertRaises(DataValidationError):
                    parse_float(value, "PREZZO")

    def test_price_components_must_be_consistent(self):
        validate_price_components(2.1151, 1.2008, 0.5329, 0.3814)

        with self.assertRaises(DataValidationError):
            validate_price_components(2.1151, 1.2008, 0.5329, 0.3)


if __name__ == "__main__":
    unittest.main()
