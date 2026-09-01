import unittest

from calculation import calculate_surcharge, price_bracket


class CalculationTests(unittest.TestCase):
    def test_calculates_surcharge_for_a_price_increase(self):
        delta, delta_pct, surcharge = calculate_surcharge(1.5, 1.65, 30)

        self.assertAlmostEqual(delta, 0.15)
        self.assertAlmostEqual(delta_pct, 10.0)
        self.assertAlmostEqual(surcharge, 3.0)

    def test_bracket_contains_the_corresponding_price(self):
        target = 1.5
        _, _, surcharge = calculate_surcharge(target, 1.65, 30)
        lower, upper = price_bracket(target, surcharge, 30)

        self.assertLess(lower, 1.65)
        self.assertGreater(upper, 1.65)

    def test_rejects_invalid_parameters(self):
        with self.assertRaises(ValueError):
            calculate_surcharge(0, 1.5, 30)
        with self.assertRaises(ValueError):
            price_bracket(1.5, 1.0, 0)


if __name__ == "__main__":
    unittest.main()
