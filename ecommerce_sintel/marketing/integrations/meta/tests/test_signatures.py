import hashlib
import hmac

from django.test import SimpleTestCase

from marketing.integrations.meta.signatures import verify_meta_webhook_signature


def _sign(secret: str, body: bytes) -> str:
    return "sha256=" + hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()


class VerifyMetaWebhookSignatureTests(SimpleTestCase):
    body = b'{"entry":[{"changes":[]}]}'
    secret = "top-secret"

    def test_valid_signature_returns_true(self):
        self.assertTrue(
            verify_meta_webhook_signature(self.secret, self.body, _sign(self.secret, self.body))
        )

    def test_wrong_secret_returns_false(self):
        self.assertFalse(
            verify_meta_webhook_signature(self.secret, self.body, _sign("other", self.body))
        )

    def test_tampered_body_returns_false(self):
        header = _sign(self.secret, self.body)
        self.assertFalse(
            verify_meta_webhook_signature(self.secret, self.body + b" ", header)
        )

    def test_empty_secret_fails_closed(self):
        self.assertFalse(
            verify_meta_webhook_signature("", self.body, _sign("anything", self.body))
        )

    def test_missing_header_returns_false(self):
        self.assertFalse(verify_meta_webhook_signature(self.secret, self.body, ""))

    def test_handles_empty_body(self):
        self.assertTrue(
            verify_meta_webhook_signature(self.secret, b"", _sign(self.secret, b""))
        )
