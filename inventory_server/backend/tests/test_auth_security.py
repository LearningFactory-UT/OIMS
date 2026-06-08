import unittest

from auth.security import DEVICE_TOKEN_ALPHABET, generate_device_token, token_hint
from settings import settings


class AuthSecurityTests(unittest.TestCase):
    def test_generated_device_token_uses_human_friendly_short_format(self):
        token = generate_device_token("tablet")

        self.assertEqual(len(token), settings.device_token_length)
        self.assertTrue(all(character in DEVICE_TOKEN_ALPHABET for character in token))

    def test_token_hint_returns_full_short_token_when_length_is_six(self):
        token = "ABC234"

        self.assertEqual(token_hint(token), token)


if __name__ == "__main__":
    unittest.main()
