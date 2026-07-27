import unittest

from server.auth import normalize_address, normalize_email


class AuthNormalizationTest(unittest.TestCase):
    def test_email_is_trimmed_and_lowercased(self):
        self.assertEqual(
            normalize_email("  Shopper@Example.COM "), "shopper@example.com"
        )

    def test_invalid_emails_are_rejected(self):
        for email in ("", "shopper", "@example.com", "shopper@", "two@@example.com"):
            with self.subTest(email=email), self.assertRaises(ValueError):
                normalize_email(email)

    def test_blank_address_is_not_saved(self):
        self.assertIsNone(normalize_address("  "))
        self.assertEqual(normalize_address("  123 Main St  "), "123 Main St")


if __name__ == "__main__":
    unittest.main()
